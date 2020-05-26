from pathlib import Path
from selenium import webdriver
import datetime
import urllib.request
import selenium.common.exceptions
import argparse
import shutil
import time
import json
import os

main_url = "https://www.instagram.com"
config_creds = "config/creds.json"
config_history = "insta_history.json"
default_sleep = 2
default_historypath = "config"
default_progressfile = "config/id_in_progress.lock"
default_filename = "instagram-%upload_date%-"
default_filepath = "data/%profile%/%upload_date%"
replace_badfilename = {"/": "_", "\\": "_", "?": "_",
                       "%": "per cent", "*": "_", ":": "_",
                       "|": "_", '"': "_", "'": "_", "<": "_",
                       ">": "_", ".": "_", "&": "-and-", ",": "_", " ": "-"}


def load_json(filename, debug=False):
    try:
        while os.path.isfile("read.lock"):
            pass
        with open("read.lock", "w") as file:
            file.write("locked reading")
        filename = os.path.normpath(filename)
        if debug:
            print("Opening json file: ", filename)
        if ".json" in filename:
            filename = filename.split(".json")[0]
        if os.path.isfile(filename + ".json"):
            with open(filename + ".json", "r") as file:
                text = json.load(file)
            if debug:
                print("Returning full dict.")
                print("Removing lock...")
            os.remove("read.lock")
            if debug:
                print("Done.")
            return text
        else:
            if debug:
                print("File not found. Returning empty dict.")
                print("Removing lock...")
            os.remove("read.lock")
            if debug:
                print("Done.")
            return {}
    except json.JSONDecodeError:
        if debug:
            print("File corrupted. Returning empty dict.")
            print("Removing lock...")
        os.remove("read.lock")
        if debug:
            print("Done.")
        return {}


def write_json(filename, write_dict, debug=False, check=True):
    try:
        while os.path.isfile("write.lock"):
            pass
        with open("write.lock", "w") as file:
            file.write("locked writing")
        filename = os.path.normpath(filename)
        if check:
            if debug:
                print("Comparing dicts...")
            compare = load_json(filename, debug=debug)
        else:
            compare = None
        if ".json" in filename:
            filename = filename.split(".json")[0]
        if compare == write_dict:
            if debug:
                print("No changes. Not writing file.")
                print("Removing lock...")
            os.remove("write.lock")
            if debug:
                print("Done.")
        else:
            if debug:
                print("Changes found. Writing file: ", filename)
            with open(filename + ".json.1", "w") as file:
                json.dump(write_dict, file)
            if debug:
                print("Write to dummy complete.")
            if os.path.isfile(filename + ".json"):
                if debug:
                    print("Creating backup file...")
                shutil.copy(filename + ".json", filename + ".json.bak")
                if debug:
                    print("Done.")
            if debug:
                print("Now changing original file...")
            shutil.move(filename + ".json.1", filename + ".json")
            if debug:
                print("Done.")
            if os.path.isfile(filename + ".json.bak"):
                if debug:
                    print("Removing backup...")
                os.remove(filename + ".json.bak")
                if debug:
                    print("Done.")
            if debug:
                print("Write complete.")
                print("Removing lock...")
            os.remove("write.lock")
            if debug:
                print("Done.")

    except Exception as e:
        if debug:
            print("Write failed.")
            print(e)
            print("Removing lock...")
        os.remove("write.lock")
        if debug:
            print("Done.")


def info_profile(profile, verbose=False, filename=""):
    keylist = ["username", "icon_url", "save_url", "time_post", "title", "type", "stored_path"]
    if profile is dict:
        for user in profile.keys():
            if verbose:
                print("Getting information about user:", user)
            for post_url in profile[user]:
                if verbose:
                    print("[" + user + "]: downloaded post URL: " + post_url)
                    for obj in range(profile[user][post_url]):
                        print("[" + user + "][" + post_url + "][" + keylist[obj] + "]: " + profile[user][post_url][obj])
                else:
                    print_dict = {user: {}}
                    for obj in range(profile[user][post_url]):
                        print_dict[user][post_url][keylist[obj]] = profile[user][post_url][obj]
                    if filename != "":
                        if ".json" in filename:
                            filename.replace(".json", "")
                        if not filename.endswith("-"):
                            filename += "-"
                        filename += "-(" + profile + ")-(" + post_url.split("/")[4] + ")"
                        write_json(filename, print_dict, check=False)
                    else:
                        print(json.dumps(print_dict))


def diff_history(history_file, name, plist, debug_read=False):
    history_json = load_json(history_file, debug=debug_read)
    if name in history_json.keys():
        return_list = []
        for post_url in plist:
            if post_url not in history_json[name]:
                return_list.append(post_url)
        return return_list
    else:
        return plist


def driver_startup(driver_visible=False, disable_login=False, driver_sleep=default_sleep,
                   use_creds="default", load_debug=False):
    options = webdriver.FirefoxOptions()
    options.headless = not driver_visible
    driver = webdriver.Firefox(options=options)
    if not disable_login:
        creds = load_json(config_creds, debug=load_debug)
        if use_creds not in creds.keys():
            print("Credentials not found. Please check the creds.json file.")
        else:
            driver.get(main_url + "/accounts/login")
            time.sleep(driver_sleep)
            driver.find_element_by_name("username").send_keys(creds[use_creds]["username"])
            driver.find_element_by_name("password").send_keys(creds[use_creds]["password"])
            driver.find_element_by_name("password").submit()
            time.sleep(driver_sleep)
    return driver


def update_profile(history_file, name, post_list, debug_read_write=False):
    update_dict = {}
    for post in diff_history(history_file, name, post_list, debug_read=debug_read_write):
        post_results = get_insta_post(post, name, write_file=not args.json,
                                      file_path=args.filepath, file_name=args.filename,
                                      debug_download=debug_output,
                                      driver_visible=visible,
                                      driver_sleep=args.sleep,
                                      write_debug=debug_read_write, no_info=args.no_info)
        history_json = load_json(history_fullpath, debug=debug_read_write)
        history_json[profile_name][post] = post_results
        write_json(history_file, history_json, debug=debug_read_write)
        update_dict[name] = {}
        update_dict[name][post] = post_results
    return update_dict


def get_insta_post(url, name, driver=None,
                   write_file=True, file_path=default_filepath, file_name=default_filename,
                   debug_download=False, driver_visible=True, driver_sleep=default_sleep,
                   write_debug=False, no_info=False):
    if not driver:
        options = webdriver.FirefoxOptions()
        options.headless = not driver_visible
        driver = webdriver.Firefox(options=options)
    driver.get(url)
    time.sleep(driver_sleep)
    if driver.execute_script('return document.getElementsByClassName("JSZAJ  _3eoV-  IjCL9  WXPwG").length') == 0:
        content_count = 1
    else:
        content_count = driver.execute_script(
            'return document.getElementsByClassName("JSZAJ  _3eoV-  IjCL9  WXPwG")[0].childElementCount')
    content_all = {}
    if debug_download:
        print("Starting post downloader with original name: ", name)
        print("Got the following target URL: ", url)
        print("Number of downloads expected from this post: ", content_count)
    if int(content_count) > 1:
        for i in range(content_count - 1):
            try:
                driver.execute_script('document.getElementsByClassName("  _6CZji ")[0].click()')
            except Exception as e:
                if debug_download:
                    print("Error clicking button: ", e)
            time.sleep(driver_sleep)
            content_dict = {"images": driver.find_elements_by_tag_name("img"),
                            "videos": driver.find_elements_by_tag_name("video")}
            for key in content_dict:
                for content in content_dict[key]:
                    a_post = driver.find_element_by_xpath(
                        "/html/body/div[1]/section/main/div/div/"
                        "article/header/div[2]/div[1]/div[1]").find_elements_by_tag_name("a")
                    insta_name = None
                    for x in a_post:
                        if "sqdOP yWX7d     _8A5w5   ZIAjV " == x.get_attribute("class"):
                            insta_name = x.text
                    if insta_name is None or insta_name != name or \
                            content.get_attribute("class") in ["_6q-tv", "s4Iyt"]:
                        continue
                    if debug_download:
                        print("Found post name: ", insta_name)
                        print("Now downloading: ", content.location)
                        print("Using key: ", key)
                    icon_url = str(driver.find_element_by_tag_name("article").find_element_by_tag_name("header") \
                                   .find_element_by_tag_name("img").get_attribute("src"))
                    save_url = str(content.get_attribute("src"))
                    time_post = datetime.datetime.strptime(driver.find_element_by_tag_name("time") \
                                                           .get_attribute("datetime").split(".")[0],
                                                           "%Y-%m-%dT%H:%M:%S")
                    if driver.execute_script('return document.getElementsByTagName("h2").length') != 0:
                        title = str(
                            driver.execute_script(
                                'return document.getElementsByTagName("h2")[0].nextSibling.textContent'))
                    else:
                        title = "__no title__"
                    content_list = [insta_name, icon_url, save_url, time_post, title, key]
                    if save_url not in content_all.keys():
                        if debug_download:
                            print("Adding URL to download list: ", save_url)
                        content_all[save_url] = content_list
    else:
        content_dict = {"images": driver.find_elements_by_tag_name("img"),
                        "videos": driver.find_elements_by_tag_name("video")}
        for key in content_dict:
            for content in content_dict[key]:
                a_post = driver.find_element_by_xpath(
                    "/html/body/div[1]/section/main/div/div/"
                    "article/header/div[2]/div[1]/div[1]").find_elements_by_tag_name("a")
                insta_name = None
                for x in a_post:
                    if "sqdOP yWX7d     _8A5w5   ZIAjV " == x.get_attribute("class"):
                        insta_name = x.text
                if insta_name is None or name != insta_name or content.get_attribute("class") in ["_6q-tv", "s4Iyt"]:
                    continue
                if debug_download:
                    print("Found post name: ", insta_name)
                    print("Now downloading: ", content.location)
                    print("Using key: ", key)
                icon_url = str(driver.find_element_by_tag_name("article").find_element_by_tag_name("header") \
                               .find_element_by_tag_name("img").get_attribute("src"))
                save_url = str(content.get_attribute("src"))
                time_post = datetime.datetime.strptime(driver.find_element_by_tag_name("time") \
                                                       .get_attribute("datetime").split(".")[0], "%Y-%m-%dT%H:%M:%S")
                if driver.execute_script('return document.getElementsByTagName("h2").length') != 0:
                    title = str(
                        driver.execute_script('return document.getElementsByTagName("h2")[0].nextSibling.textContent'))
                else:
                    title = "__no title__"
                content_list = [insta_name, icon_url, save_url, time_post, title, key]
                if save_url not in content_all.keys():
                    content_all[save_url] = content_list
    if not write_file:
        driver.quit()
        return content_all
    for saves in content_all.keys():
        if debug_download:
            print("Now working on: ", content_all[saves])
        name = content_all[saves][0]
        icon_url = content_all[saves][1]
        save_url = content_all[saves][2]
        time_post = content_all[saves][3].strftime("%Y-%m-%d_%H-%M-%S")
        title = content_all[saves][4]
        key = content_all[saves][5]
        result_list = [name, main_url, icon_url, time_post, title, key, url, save_url]
        file_title = title
        file_profile = name
        for badchar in replace_badfilename.keys():
            file_title = file_title.replace(badchar, replace_badfilename[badchar])
            file_profile = file_profile.replace(badchar, replace_badfilename[badchar])
        local_filename, headers = urllib.request.urlretrieve(save_url)
        file_path = file_path.replace("%title%", file_title) \
            .replace("%upload_date%", time_post) \
            .replace("%profile%", file_profile)
        file_name = file_name.replace("%title%", file_title) \
            .replace("%upload_date%", time_post) \
            .replace("%profile%", file_profile)
        file_name = file_name + local_filename.rsplit(".", maxsplit=1)[1]
        os.makedirs(file_path, exist_ok=True)
        full_path = os.path.normpath(file_path + "/" + file_name)
        content_all[saves].append(full_path)
        shutil.move(local_filename, full_path)
        if not no_info:
            write_json(full_path + ".info", {title.encode(): [s.encode() for s in result_list]}, debug=write_debug)
    driver.quit()
    return content_all


def check_profile_url(url, driver, no_login=False, driver_sleep=default_sleep,
                      debug_download=False):
    try:
        if url.startswith(main_url):
            return_list = []
            driver.get(url)
            one_left = False
            while not one_left:
                time.sleep(driver_sleep)
                article = driver.find_element_by_tag_name("article")
                divs = article.find_elements_by_tag_name("div")
                test_load = True
                if not no_login:
                    for div in divs:
                        if div.get_attribute("class") == "_4emnV":
                            test_load = False
                if test_load:
                    one_left = True
                    post_div = []
                    xdiv = article.find_elements_by_tag_name("div")
                    for x in xdiv:
                        if x.get_attribute("class") == "Nnq7C weEfm":
                            post_div.append(x)
                    for pd in reversed(post_div):
                        xpd = pd.find_elements_by_tag_name("a")
                        for post in reversed(xpd):
                            post_url = post.get_attribute("href")
                            return_list.append(post_url)
                else:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.quit()
            if not one_left:
                if debug_download:
                    print("Page seems to be broken. URL: " + url)
            return return_list
        else:
            if debug_download:
                print("Not an Instagram URL! Did someone change the file?")
                print("Shutting down in order to prevent further damage.")
            exit(2)
    except selenium.common.exceptions.WebDriverException as e:
        try:
            driver.quit()
        except Exception:
            pass
        if debug_download:
            print("Removed watch after error occured in download_profile_url()")
            print("Exception:", e)


def download_profile_url(url, name, driver, no_login=False, driver_sleep=default_sleep,
                         file_path=default_filepath, file_name=default_filename, write_file=True, no_info=False,
                         write_debug=False, debug_download=False, driver_visible=False):
    try:
        if url.startswith(main_url):
            return_dict = {}
            driver.get(url)
            one_left = False
            while not one_left:
                time.sleep(driver_sleep)
                article = driver.find_element_by_tag_name("article")
                divs = article.find_elements_by_tag_name("div")
                test_load = True
                if not no_login:
                    for div in divs:
                        if div.get_attribute("class") == "_4emnV":
                            test_load = False
                if test_load:
                    one_left = True
                    post_div = []
                    xdiv = article.find_elements_by_tag_name("div")
                    for x in xdiv:
                        if x.get_attribute("class") == "Nnq7C weEfm":
                            post_div.append(x)
                    for pd in reversed(post_div):
                        xpd = pd.find_elements_by_tag_name("a")
                        for post in reversed(xpd):
                            post_url = post.get_attribute("href")
                            return_dict[post_url] = get_insta_post(post_url, name, write_file=write_file,
                                                                   file_path=file_path, file_name=file_name,
                                                                   debug_download=debug_download,
                                                                   driver_visible=driver_visible,
                                                                   driver_sleep=driver_sleep,
                                                                   write_debug=write_debug, no_info=no_info)
                else:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.quit()
            if not one_left:
                if debug_download:
                    print("Page seems to be broken. URL: " + url)
            return return_dict
        else:
            if debug_download:
                print("Not an Instagram URL! Did someone change the file?")
                print("Shutting down in order to prevent further damage.")
            exit(2)
    except selenium.common.exceptions.WebDriverException as e:
        try:
            driver.quit()
        except Exception:
            pass
        if debug_download:
            print("Removed watch after error occured in download_profile_url()")
            print("Exception:", e)


cwd = os.getcwd()
default_infopath = cwd
default_infoname = "insta_info-"
os.chdir(Path(__file__).parent.absolute())

parser = argparse.ArgumentParser(description="Download Instagram posts of provided profile URLs/files\n"
                                             "Github: https://github.com/jeliebig/instagram-downloader",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                 usage="%(prog)s (-a | -u) profiles [options]")

method_group = parser.add_mutually_exclusive_group(required=True)
history_group = parser.add_mutually_exclusive_group()
login_group = parser.add_mutually_exclusive_group()
json_group = parser.add_argument_group("Arguments dealing with json output",
                                       "The json file contains the following information:\n"
                                       "    -username\n"
                                       "    -icon_url\n"
                                       "    -save_url\n"
                                       "    -time_post\n"
                                       "    -title\n"
                                       "    -type\n"
                                       "    [-stored_path]")
file_group = parser.add_argument_group("Arguments dealing with files")

method_group.add_argument("-a", "--all",
                          help="downloads every post of the provided profile URLs/files\n"
                               "Note:\n"
                               "    This option does not check the contents of the history file!\n"
                               "    If you already added one of the provided profiles the history will be overwritten.",
                          action="store_true")
method_group.add_argument("-u", "--update",
                          help="downloads the newest posts of the provided profile URLs/files",
                          action="store_true")

history_group.add_argument("-hp", "--history_path",
                           help="changes the default history directory to use for downloaded Instagram posts",
                           default=default_historypath, type=str)
history_group.add_argument("-nh", "--no_history",
                           help="disables using the Instagram history file (reading and writing)",
                           action="store_true")

login_group.add_argument("-c", "--creds",
                         help="selects the credentials to be used to log in to Instagram from the json config",
                         type=str, default="default")
login_group.add_argument("-nl", "--no_login",
                         help="disables Instagram login, you may not be able to download all posts from a profile\n"
                              "Note: Use this option when using -u to speed up the process",
                         action="store_true")

file_group.add_argument("-fp", "--filepath",
                        help="changes the default download directory for saving Instagram posts",
                        type=str, default=default_filepath)
file_group.add_argument("-fn", "--filename",
                        help="changes the default output filename scheme - \n"
                             "using %%title%% allows you to use the title of a post in the filename",
                        type=str, default=default_filename)

json_group.add_argument("-j", "--json",
                        help="returns a generated json file with information about the provided profile URLs/files",
                        action="store_true")
json_group.add_argument("-jp", "--json_path",
                        help="changes the default output directory for generated json information",
                        type=str, default=default_infopath)
json_group.add_argument("-jn", "--json_filename",
                        help="changes the default output filename scheme for generated json information - \n"
                             "if an empty string is provided the output will be redirected to the console",
                        type=str, default=default_infoname)

parser.add_argument("-v", "--verbose",
                    help="displays more information about the script - \n"
                         " using it twice displays even more information. - \n"
                         " using it three times makes the browser visible",
                    action="count")
parser.add_argument("-s", "--sleep",
                    help="sets the wait time for websites to load, depends on your computer and internet speed",
                    type=int, default=default_sleep)
parser.add_argument("-ni", "--no_info",
                    help="disables writing .info files for downloaded Instagram posts",
                    action="store_true")
parser.add_argument("-rp", "--remove_profile",
                    help="removes the provided profiles if they are files",
                    action="store_true")
parser.add_argument("-pf", "--progress_file",
                    help="generates an empty file on startup and deletes it after execution\n"
                         "Note: This makes the script wait until the file is removed "
                         "if the file has already been created.",
                    action="store_true")
parser.add_argument("profiles",
                    help="specifies one or more profile URLs and/or files to download",
                    type=str, nargs="+")
args = parser.parse_args()

visible = args.verbose >= 3
debug_file = args.verbose >= 2
debug_output = args.verbose >= 1

history_fullpath = args.history_path + "/" + config_history
os.makedirs(args.history_path, exist_ok=True)

if args.progress_file:
    if debug_output:
        if os.path.isfile(default_progressfile):
            print("Waiting until in_progress file is removed...")
    while os.path.isfile(default_progressfile):
        pass
    if debug_file:
        print("Writing in_progress file...")
    with open(default_progressfile, "w") as file:
        file.write("")
    if debug_output:
        print("Starting execution...")


if args.all:
    for profile_num in range(len(args.profiles)):
        profile = args.profiles[profile_num]
        if profile.startswith(main_url):
            profile_name = profile.split("/")[3]
            profile_dict = download_profile_url(profile, profile_name,
                                                driver_startup(driver_visible=visible,
                                                               disable_login=args.no_login,
                                                               driver_sleep=args.sleep,
                                                               use_creds=args.creds,
                                                               load_debug=debug_file),
                                                no_login=args.no_login, driver_sleep=args.sleep,
                                                file_path=args.filepath, file_name=args.filename,
                                                write_debug=debug_file, no_info=args.no_info, write_file=not args.json,
                                                debug_download=debug_output, driver_visible=visible)

            history = load_json(history_fullpath, debug=debug_file)
            history[profile_name] = profile_dict
            write_json(history_fullpath, history)
            json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
            if args.json and args.json_filename != "":
                info_profile(profile_dict, filename=json_path)
            elif args.json and args.json_filename == "":
                info_profile(profile_dict, filename="")
        else:
            profile = os.path.normpath(cwd + "/" + profile)
            try:
                with open(profile, "r") as file:
                    text = [x.replace("\n", "") for x in file.readlines()]
            except FileNotFoundError:
                print("Error: The following file does not exist:", profile)
                text = []
            for line in text:
                if line.startswith(main_url):
                    profile_name = line.split("/")[3]
                    profile_dict = download_profile_url(line, profile_name,
                                                        driver_startup(driver_visible=visible,
                                                                       disable_login=args.no_login,
                                                                       driver_sleep=args.sleep,
                                                                       use_creds=args.creds,
                                                                       load_debug=debug_file),
                                                        no_login=args.no_login, driver_sleep=args.sleep,
                                                        file_path=args.filepath, file_name=args.filename,
                                                        write_debug=debug_file, no_info=args.no_info,
                                                        write_file=not args.json,
                                                        debug_download=debug_output, driver_visible=visible)

                    history = load_json(history_fullpath, debug=debug_file)
                    history[profile_name] = profile_dict
                    write_json(history_fullpath, history)
                    json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
                    if args.json and args.json_filename != "":
                        info_profile(profile_dict, filename=json_path)
                    elif args.json and args.json_filename == "":
                        info_profile(profile_dict, filename="")
                else:
                    if debug_output:
                        print("Ignoring wrong URL. File: '" + profile + "' Line: '" + line + "'")
        if args.remove_profile:
            try:
                os.remove(profile)
                if profile_num != 0:
                    profile_num -= 1
            except FileNotFoundError:
                pass
elif args.update:
    for profile_num in range(len(args.profiles)):
        profile = args.profiles[profile_num]
        if profile.startswith(main_url):
            profile_name = profile.split("/")[3]
            profile_list = check_profile_url(profile,
                                             driver_startup(driver_visible=visible,
                                                            disable_login=args.no_login,
                                                            driver_sleep=args.sleep,
                                                            use_creds=args.creds,
                                                            load_debug=debug_file),
                                             no_login=args.no_login, driver_sleep=args.sleep,
                                             debug_download=debug_output)

            profile_dict = update_profile(history_fullpath, profile_name, profile_list)
            json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
            if args.json and args.json_filename != "":
                info_profile(profile_dict, filename=json_path)
            elif args.json and args.json_filename == "":
                info_profile(profile_dict, filename="")
        else:
            profile = os.path.normpath(cwd + "/" + profile)
            try:
                with open(profile, "r") as file:
                    text = [x.replace("\n", "") for x in file.readlines()]
            except FileNotFoundError:
                print("Error: The following file does not exist:", profile)
                text = []
            for line in text:
                if line.startswith(main_url):
                    profile_name = line.split("/")[3]
                    profile_list = check_profile_url(line,
                                                     driver_startup(driver_visible=visible,
                                                                    disable_login=args.no_login,
                                                                    driver_sleep=args.sleep,
                                                                    use_creds=args.creds,
                                                                    load_debug=debug_file),
                                                     no_login=args.no_login, driver_sleep=args.sleep,
                                                     debug_download=debug_output)

                    profile_dict = update_profile(history_fullpath, profile_name, profile_list)
                    json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
                    if args.json and args.json_filename != "":
                        info_profile(profile_dict, filename=json_path)
                    elif args.json and args.json_filename == "":
                        info_profile(profile_dict, filename="")
                else:
                    if debug_output:
                        print("Ignoring wrong URL. File: '" + profile + "' Line: '" + line + "'")
        if args.remove_profile:
            try:
                os.remove(profile)
                if profile_num != 0:
                    profile_num -= 1
            except FileNotFoundError:
                pass

if args.progress_file:
    if debug_file:
        print("Removing in_progress file...")
    os.remove(default_progressfile)
