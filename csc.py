#!/usr/bin/env python3 -u

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from datetime import datetime
from datetime import timedelta

import subprocess
import time
import json
import sys


COLOR_DELETE = '\033[31;1m'
COLOR_FAIL = '\033[31m'
COLOR_IRRELEVANT = '\033[34m'
COLOR_OK = '\033[32m'
COLOR_RESET = '\033[0m'
COLOR_WARN = '\033[33m'

BULLET = f'{COLOR_DELETE}*{COLOR_RESET}'


def main():

    args = parse_args()

    count_log_groups = 0
    count_log_streams = 0
    count_bytes_before = 0
    count_bytes_after = 0

    exceptions = []

    resp, code = shell_exec(['aws', 'logs', 'describe-log-groups'])
    if code != 0:
        log_error(resp, code)
        exit(code)


    for group in resp['logGroups']:

        count_bytes_before += group['storedBytes']
        group_name = group['logGroupName']
        stream_name = None

        try:
            resp, code = shell_exec(['aws', 'logs', 'describe-log-streams', '--descending', '--log-group-name', group_name]) # sort direction: newest to oldest
            if code != 0:
                log_error(resp, code)
                continue

            log_streams = resp['logStreams']

            if not log_streams:
                print(f'no streams in group {group_name} (gonna skip)')
                continue

            for i, log_stream in enumerate(log_streams):
                latest_log_occurrence = log_stream['lastEventTimestamp']
                stream_name = log_stream['logStreamName']

                if older_than_days(7, latest_log_occurrence):
                    if i == 0: # if the most recent stream contains no entries younger than 7 days, delete the group
                        print(f'deleting {COLOR_DELETE}group{COLOR_RESET} {group_name}'.strip())

                        if not args.dry:
                            resp, code = shell_exec(['aws', 'logs', 'delete-log-group', '--log-group-name', group_name])
                            if code != 0:
                                print(f'{COLOR_FAIL}[FAILED]{COLOR_RESET} (error code: {code})')
                                continue

                        count_log_groups += 1
                        count_log_streams += len(log_streams)

                        print(f'{COLOR_OK}[OK] {COLOR_IRRELEVANT}(total: {count_log_groups}){COLOR_RESET}')
                        break
                    else: # if any subsequent stream contains no entries younger than 7 days, delete the stream
                        print(f"deleting {COLOR_DELETE}stream{COLOR_RESET} {stream_name} from group {group_name}".strip())

                        if not args.dry:
                            resp, code = shell_exec(['aws', 'logs', 'delete-log-stream', '--log-group-name', group_name, '--log-stream-name', stream_name])
                            if code != 0:
                                print(f'{COLOR_FAIL}[FAILED]{COLOR_RESET} (error code: {code})')
                                continue

                        count_log_streams += 1
                        print(f'{COLOR_OK}[OK] {COLOR_IRRELEVANT}(total: {count_log_streams}){COLOR_RESET}')
                else:
                    if i == 0:
                        print(f'{COLOR_IRRELEVANT}ignoring group {group_name}{COLOR_RESET}')
                        continue
                    print(f"{COLOR_IRRELEVANT}ignoring stream {stream_name} of group {group_name}{COLOR_RESET}")

                stream_name = None

        except BaseException as e:
            if not stream_name:
                print(f"{COLOR_WARN}[WARN]{COLOR_RESET} there was a problem with log group {group_name}: {e}")
                exceptions.append(group_name)
            else:
                print(f"{COLOR_WARN}[WARN]{COLOR_RESET} there was a problem with stream {stream_name} of group {group_name}: {e}")
                exceptions.append(f'{group_name} > {stream_name}')
            continue

    resp, code = shell_exec(['aws', 'logs', 'describe-log-groups'])
    if code != 0:
        log_error(resp, code)

    for group in resp['logGroups']:
        count_bytes_after += group['storedBytes']

    print_summary(count_log_groups, count_log_streams, count_bytes_before, count_bytes_after, exceptions)


def parse_args():
    parser = ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=RawTextHelpFormatter
    )

    parser.add_argument('-d', '--dry', help='perform a "dry run" to simulate what would happen without deleting anything', action='store_true')
    required = parser.add_argument_group('required arguments')
    required.add_argument('-r', '--retention', help='provide number of days to delete all log-streams older than that', type=int, required=True)

    return parser.parse_args()


def shell_exec(args):
    result = None
    try: 
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return json.loads(result.stdout.decode('utf-8')), result.returncode
    except BaseException as e:
        return result.stderr.decode('utf-8').strip(), result.returncode
        

def log_error(error, code):
    print(f"{COLOR_FAIL}[ERROR]{COLOR_RESET} {error} [exit code: {code}]")


def older_than_days(time_period, epoch_unix_timestamp):
    converted = datetime.utcfromtimestamp( int(epoch_unix_timestamp / 1000) )
    return converted < (datetime.today() - timedelta(days=time_period))


def print_summary(count_log_groups, count_log_streams, count_bytes_before, count_bytes_after, exceptions):
    print(f'\n{COLOR_RESET}-------------{COLOR_RESET}')
    print(f'{COLOR_OK}S U M M A R Y{COLOR_RESET}\n')

    print(f'Deleted log groups: {COLOR_OK}{count_log_groups}{COLOR_RESET}')
    print(f'Deleted log streams: {COLOR_OK}{count_log_streams}{COLOR_RESET}')
    print(f'Total log size before and after execution: {COLOR_OK}{count_bytes_before}{COLOR_RESET} -> {COLOR_OK}{count_bytes_after}{COLOR_RESET} (bytes)')

    print(f'\nSkipped due to problems (please review and delete manually):')
    for ex in exceptions:
        print(BULLET, ex)

    print('')


description="""Cleans up your messy crime scene inside CloudWatch :)

Before execution, the aws-cli must be installed and your credentials must 
be sourced by the shell - alternatively, the cli must be 'aws configure'd.

This script runs through all your log groups and their corresponding log 
streams and searches for log entries older than the specified number of 
days. If a log stream contains no entries younger than that number, it 
is considered outdated and gets deleted. If a log group contains only 
outdated log streams, it gets deleted, as well.

When finished, the total number of deleted groups and streams is 
displayed and the log size before and after the run is presented."""

epilog=f"""Examples:

Delete all log streams older than 10 days:
{sys.argv[0]} -r 10
{sys.argv[0]} --retention=10

Perform a dry-run to see what would be happen:
{sys.argv[0]} -d -r 10
{sys.argv[0]} --dry --retention=10
"""


main()
