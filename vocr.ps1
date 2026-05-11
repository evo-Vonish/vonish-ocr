$env:VONISH_HOME = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m cli.main @args
