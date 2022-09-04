# Crime scene cleaner
🧹 Helps you to get rid of dead CloudWatch log groups and streams 🧹

### How to use
1. Install the aws cli
1. Download your aws credentials
1. Source them into your shell: `. /path/to/your/credentials.txt` (or configure your cli via `aws configure`)
1. Simulate a run that would delete all log streams containing no logs younger than 10 days: `./csc.py --dry --retention=10` or `./csc.py -d -r 10`
1. If the results meet your expectations, remove the dry flag and repeat: `./csc.py -r 10`

For more details, run the script with the help flag: `./csc.py -h`
