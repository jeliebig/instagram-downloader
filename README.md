# Instagram Downloader
A little python tool to download all or just the recent Instagram posts of provided profiles.

## Syntax (How to use)
Here is the (slightly better formatted) help output of my script:
```
test@test:~/insta-downloader$ ./insta-downloader.py -h
usage: insta-downloader.py (-a | -u) profiles [options]

Download Instagram posts of provided profile URLs/files
Github: https://github.com/jeliebig/instagram-downloader

positional arguments:
  profiles              specifies one or more profile URLs and/or files to download

optional arguments:
  -h, --help            show this help message and exit

  -a, --all             downloads every post of the provided profile URLs/files
                        Note: This option does not check the contents of the history file!
                                If you already added one of the provided profiles the history will be overwritten. (default: False)

  -u, --update          downloads the newest posts of the provided profile URLs/files (default: False)

  -hp HISTORY_PATH, --history_path HISTORY_PATH
                        changes the default history directory to use for downloaded Instagram posts (default: config)

  -nh, --no_history     disables using the Instagram history file (reading and writing) (default: False)
  -c CREDS, --creds CREDS
                        selects the credentials to be used to log in to Instagram from the json config (default: default)

  -nl, --no_login       disables Instagram login, you may not be able to download all posts from a profile
                         Note: Use this option when using -u to speed up the process (default: False)

  -v, --verbose         displays more information about the script
                         using it twice displays even more information
                         using it three times makes the browser visible (default: None)

  -s SLEEP, --sleep SLEEP
                        sets the wait time for websites to load, depends on your computer and internet speed (default: 2)

  -ni, --no_info        disables writing .info files for downloaded Instagram posts (default: False)

  -rp, --remove_profile
                        removes the provided profiles if they are files (default: False)

  -pf, --progress_file
                        generates an empty file on startup and deletes it after execution
                        Note: This makes the script wait until the file is removed if the file has already been created. (default: False)

Arguments dealing with json output:
  The json file contains the following information: 
                    [username; icon_url; save_url; time_post; title; type; (stored_path)]

  -j, --json            returns a generated json file with information about the provided profile URLs/files (default: False)

  -jp JSON_PATH, --json_path JSON_PATH
                        changes the default output directory for generated json information (default: /home/test/instagram-downloader)

  -jn JSON_FILENAME, --json_filename JSON_FILENAME
                        changes the default output filename scheme for generated json information
                        if an empty string is provided the output will be redirected to the console (default: insta_info-)

Arguments dealing with files:
  -fp FILEPATH, --filepath FILEPATH
                        changes the default download directory for saving Instagram posts (default: data/%profile%/%upload_date%)

  -fn FILENAME, --filename FILENAME
                        changes the default output filename scheme 
                            using %title% allows you to use the title of a post in the filename (default: instagram-%upload_date%-)
```


## How to setup

You can simply clone the repository and if you already installed selenium and used it with Firefox before you are good to go.

If that is not the case you could install every requirement one by one from the list below or use these commands that'll do it for you.

Linux (you might need to enter your sudo password):
```bash
git clone https://github.com/jeliebig/instagram-downloader
python3 instagram-downloader/install-requirements.py
python3 -m pip install -r instagram-downloader/requirements.txt
```

Windows:

Install [Git for Windows](https://gitforwindows.org/)

Then you should be able to run these commands:
```cmd
git clone https://github.com/jeliebig/instagram-downloader
python instagram-downloader/install-requirements.py
python -m pip install -r instagram-downloader/requirements.txt
```

## Requirements

I am using python3.8 for this project but I am sure it will work with every version after 3.3.
But because I am using urllib.request to download files locally I expect this script to break with newer versions of python3.
These are the requirements so far:
- [Python3](https://www.python.org/)
- [Selenium](https://selenium-python.readthedocs.io/installation.html)
- [Firefox](https://www.mozilla.org/en-US/firefox/) (This could be changed by the user in the future)
- [Geckodriver](https://github.com/mozilla/geckodriver/releases) (Needed to control the firefox browser)
- [Instagram Account](https://www.instagram.com/accounts/emailsignup/) (needed to scroll down larger profiles)
