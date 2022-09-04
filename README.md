# Crime Scene Cleaner
Helps you to get rid of dead CloudWatch log groups and streams

### How to use
0. Download your aws credentials
0. Source them into your shell: `. /path/to/your/credentials.txt` (or configure your cli via `aws configure`)
0. Simulate a run that would delete all log streams containing no logs younger than 10 days: `./csc.py --dry --retention=10` or `./csc.py -d -r 10`
0. If the results meet your expectations, remove the dry flag and repeat: `./csc.py -r 10`

For more details, run the script with the help flag: `./csc.py -h`
