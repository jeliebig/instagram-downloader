import urllib.request
import os
import subprocess
import platform
import shutil

gecko_here = False
gecko_linux = "https://github.com/mozilla/geckodriver/releases/download/%version%/geckodriver-%version%-linux64.tar.gz"
gecko_win = "https://github.com/mozilla/geckodriver/releases/download/%version%/geckodriver-%version%-win64.zip"

r = urllib.request.urlopen("https://github.com/mozilla/geckodriver/releases/latest")
gecko_version = r.geturl().rsplit("/", maxsplit=1)[1]
r.close()

pathvar = os.environ["PATH"]
if platform.system() == "Windows":
    pathlist = pathvar.split(";")
    path_win = False
    for path in pathlist:
        if os.getcwd() in path:
            path_win = True
            break
    if not path_win:
        print("Please install firefox if you haven't already.")
        input("Press Enter after you finished installation...")
    else:
        ask_win = ""
        while ask_win.lower() != "y" and ask_win.lower() != "n":
            ask_win = input("Do you have geckodriver installed already? (y/n): ")
        if ask_win.lower() == "y":
            print("Installation finished.")
            exit(0)
        else:
            print("Downloading geckodriver...")
            download_url = gecko_win.replace("%version%", gecko_version)
            print("Getting version:", gecko_version)
            print("Download link:", download_url)
            local_filename, headers = urllib.request.urlretrieve(download_url)
            shutil.move(local_filename, os.getcwd() + "\\" + "geckodriver.zip")
            print("Please extract the downloaded geckodriver.zip")
            input("Press Enter after you finished extracting geckodriver...")
            if "geckodriver.exe" in os.listdir(os.getcwd()):
                os.system('setx path "%path%;' + os.getcwd() + "\\geckodriver.exe" + '"')
                print("Sucessfully installed geckodriver to: ", os.getcwd() + "\\geckodriver.exe")
            elif "geckodriver" in os.listdir(os.getcwd()):
                os.system('setx path "%path%;' + os.getcwd() + "\\geckodriver\\geckodriver.exe" + '"')
                print("Sucessfully installed geckodriver to: ", os.getcwd() + "\\geckodriver\\geckodriver.exe")
            else:
                unzip_path = input("Please provide the extraction path for geckodriver: ")
                if "geckodriver.exe" not in unzip_path:
                    unzip_path = unzip_path + "\\geckodriver.exe"
                    os.system('setx path "%path%;' + unzip_path + '"')
                print("Sucessfully installed geckodriver to: ", unzip_path)
elif platform.system() == "Linux":
    pathlist = pathvar.split(":")
    home = os.path.expanduser("~")
    if os.path.normpath(home + "/.local/bin") in pathlist:
        path_linux = True
    else:
        path_linux = False
    for path in pathlist:
        if "geckodriver" in os.listdir(path):
            gecko_here = True
            break
    print("Running 'sudo apt install firefox -y'")
    subprocess.call("sudo apt install firefox -y".split())
    print("Done.")
    if not gecko_here:
        print("Downloading latest geckodriver...")
        download_url = gecko_linux.replace("%version%", gecko_version)
        print("Getting version:", gecko_version)
        print("Download link:", download_url)
        local_filename, headers = urllib.request.urlretrieve(download_url)
        os.makedirs("~/.local/bin", exist_ok=True)
        shutil.move(local_filename, "~/.local/bin/geckodriver.tar.gz")
        os.chdir("~/.local/bin")
        os.system("tar -xvzf geckodriver.tar.gz")
        subprocess.call("sudo chmod +x " + os.path.normpath(home + "/" + "geckodriver"))
        os.remove("geckodriver.tar.gz")
        print("Successfully installed geckodriver to '~/.local/bin/geckodriver'")
        if not path_linux:
            os.system("export PATH=$PATH:~/.local/bin")
            print("Temporarily added '~/.local/bin' to path.")
            print("If you want to permanently add it to the path variable "
                  "append the following lines to the end of your '.profile' file:")
            print()
            print("# set PATH so it includes user's private bin if it exists\n"
                  'if [ -d "$HOME/.local/bin" ] ; then\n'
                  '    PATH="$HOME/.local/bin:$PATH"\n'
                  'fi')
            print()
else:
    print("Sorry, I can't do anything for you. Please install the requirements manually.")

print("Installation finished.")
exit(0)
