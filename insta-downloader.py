from pathlib import Path
from selenium import webdriver
import datetime
import urllib.request
import selenium.common.exceptions
import argparse
import shutil
import time
import logging
import logging.handlers
import json
import os

main_url = ["https://www.instagram.com", "https://instagram.com"]
config_logfile = "insta-downloader.log"
config_creds = "config/creds.json"
config_history = "insta_history.json"
default_sleep = 2
default_historypath = "config"
default_progressfile = "config/id_in_progress.lock"
default_filename = "instagram-%upload_date%"
default_filepath = "data/%profile%/%upload_date%"
replace_badfilename = {"/": "_", "\\": "_", "?": "_",
                       "%": "per cent", "*": "_", ":": "_",
                       "|": "_", '"': "_", "'": "_", "<": "_",
                       ">": "_", ".": "_", "&": "-and-", ",": "_", " ": "-"}


def load_json(filename):
    try:
        while os.path.isfile("read.lock"):
            time.sleep(1)
        with open("read.lock", "w") as file:
            file.write("locked reading")
        filename = os.path.normpath(filename)
        log.debug("Opening json file: %s", filename)
        if ".json" in filename:
            filename = filename.split(".json")[0]
        if os.path.isfile(filename + ".json"):
            with open(filename + ".json", "r") as file:
                text = json.load(file)
            log.debug("Returning full dict.")
            log.debug("Removing lock...")
            os.remove("read.lock")
            log.debug("Done.")
            return text
        else:
            log.warning("File: %s not found. Returning empty dict.", filename)
            log.debug("Removing lock...")
            os.remove("read.lock")
            log.debug("Done.")
            return {}
    except json.JSONDecodeError:
        log.warning("File: %s corrupted. Returning empty dict.", filename)
        log.debug("Removing lock...")
        os.remove("read.lock")
        log.debug("Done.")
        return {}


def write_json(filename, write_dict, check=True):
    try:
        while os.path.isfile("write.lock"):
            time.sleep(1)
        with open("write.lock", "w") as file:
            file.write("locked writing")
        filename = os.path.normpath(filename)
        if check:
            log.debug("Comparing dicts...")
            compare = load_json(filename)
        else:
            compare = None
        if ".json" in filename:
            filename = filename.split(".json")[0]
        if compare == write_dict:
            log.debug("No changes. Not writing file.")
            log.debug("Removing lock...")
            os.remove("write.lock")
            log.debug("Done.")
        else:
            log.debug("Changes found. Writing file: %s", filename)
            with open(filename + ".json.1", "w") as file:
                json.dump(write_dict, file, indent=4)
            log.debug("Write to dummy complete.")
            if os.path.isfile(filename + ".json"):
                log.debug("Creating backup file...")
                shutil.copy(filename + ".json", filename + ".json.bak")
                log.debug("Done.")
            log.debug("Now changing original file...")
            shutil.move(filename + ".json.1", filename + ".json")
            log.debug("Done.")
            if os.path.isfile(filename + ".json.bak"):
                log.debug("Removing backup...")
                os.remove(filename + ".json.bak")
                log.debug("Done.")
            log.debug("Write complete.")
            log.debug("Removing lock...")
            os.remove("write.lock")
            log.debug("Done.")

    except Exception as e:
        log.exception("Write failed. The following exception occurred: %s", e)
        log.debug("Removing lock...")
        os.remove("write.lock")
        log.debug("Done.")


def info_profile(profile, filename=""):
    try:
        keylist = ["username", "icon_url", "save_url", "time_post", "title", "type", "stored_path"]
        if filename != "":
            if ".json" in filename:
                filename.replace(".json", "")
            if not filename.endswith("-"):
                filename += "-"
            filename += "-(%user%)-(%post_url%)"
        for user in profile.keys():
            log.info("Processing information about user: %s", user)
            for post_url in profile[user]:
                print_dict = {user: {}}
                if post_url not in print_dict[user].keys():
                    print_dict[user][post_url] = {}
                log.info("[%s]: downloading post URL: %s", user, post_url)
                for save_url in profile[user][post_url].keys():
                    if save_url not in print_dict[user][post_url]:
                        print_dict[user][post_url][save_url] = {}
                        log.debug("List of saved URL: %s", profile[user][post_url][save_url])
                    for obj in range(len(profile[user][post_url][save_url])):
                        print_dict[user][post_url][save_url][keylist[obj]] = profile[user][post_url][save_url][obj]
                if filename != "":
                    write_json(filename.replace("%user%", user).replace("%post_url%", post_url.split("/")[4]),
                               print_dict, check=False)
                else:
                    print(json.dumps(print_dict))
            log.info("Finished processing information about user: %s", user)
    except Exception as e:
        log.exception("Could not process information. The following exception occurred: %s", e)


def diff_history(history_file, name, plist):
    try:
        history_json = load_json(history_file)
        if name in history_json.keys():
            return_list = []
            for post_url in plist:
                if post_url not in history_json[name]:
                    return_list.append(post_url)
            return return_list
        else:
            return plist
    except Exception as e:
        log.exception("Could not create diff history dict. The following exception occurred: %s", e)
        return None


def driver_startup(driver_visible=False, disable_login=False, driver_sleep=default_sleep,
                   use_creds="default"):
    try:
        options = webdriver.FirefoxOptions()
        options.headless = not driver_visible
        driver = webdriver.Firefox(options=options)
    except Exception as e:
        log.exception("Could not start Firefox. The following exception occurred: %s", e)
        return None
    if not disable_login:
        creds = load_json(config_creds)
        if use_creds not in creds.keys():
            log.error("Credentials not found. Please check the creds.json file.")
        else:
            try:
                driver.get(main_url[0] + "/accounts/login")
                time.sleep(driver_sleep)
                driver.find_element_by_name("username").send_keys(creds[use_creds]["username"])
                driver.find_element_by_name("password").send_keys(creds[use_creds]["password"])
                driver.find_element_by_name("password").submit()
                time.sleep(driver_sleep)
            except Exception as e:
                log.exception("Could not login. The following exception occurred: %s", e)
                return None
    return driver


def update_profile(driver, history_file, name, post_list):
    try:
        update_dict = {}
        for post in diff_history(history_file, name, post_list):
            post_results = get_insta_post(post, name, write_file=not args.json, driver=driver,
                                          file_path=args.filepath, file_name=args.filename,
                                          driver_visible=visible, driver_sleep=args.sleep, no_info=args.no_info)
            if post_results is not None:
                history_json = load_json(history_fullpath)
                if profile_name not in history_json.keys():
                    history_json[profile_name] = {}
                if post not in history_json[profile_name].keys():
                    history_json[profile_name][post] = {}
                history_json[profile_name][post] = post_results
                write_json(history_file, history_json)
                update_dict[name] = {}
                update_dict[name][post] = post_results
            else:
                log.error("Detected crash in get_insta_post. Exiting...")
                return None
        return update_dict
    except Exception as e:
        log.exception("Could not download recent posts. The following exception occurred: %s", e)
        return None


def get_content(driver, name=""):
    content_all = {}
    content_dict = {"images": driver.find_elements_by_tag_name("img"),
                    "videos": driver.find_elements_by_tag_name("video")}
    for key in content_dict:
        for content in content_dict[key]:
            a_post = driver.find_element_by_xpath(
                "/html/body/div[1]/section/main/div/div/article/div/header/div[2]/div[1]").find_elements_by_tag_name(
                "a")
            insta_name = None
            for x in a_post:
                if "sqdOP yWX7d     _8A5w5   ZIAjV " == x.get_attribute("class"):
                    insta_name = x.text
            if insta_name is None or insta_name != name or \
                    content.get_attribute("class") in ["_6q-tv", "s4Iyt"]:
                continue
            log.debug("Found post name: %s", insta_name)
            log.debug("Now inspecting: %s", content.get_attribute("src"))
            log.debug("Using key: %s", key)
            icon_url = str(driver.find_element_by_tag_name("article").find_element_by_tag_name("header") \
                           .find_element_by_tag_name("img").get_attribute("src"))
            save_url = str(content.get_attribute("src"))
            time_post = datetime.datetime.strptime(driver.find_element_by_tag_name("time") \
                                                   .get_attribute("datetime").split(".")[0],
                                                   "%Y-%m-%dT%H:%M:%S")
            if driver.execute_script('return document.getElementsByTagName("h2").length') != 0:
                title = str(
                    driver.execute_script(
                        'return document.getElementsByTagName("h2")[0].nextSibling.innerText'))
            else:
                title = "__no title__"
            content_list = [insta_name, icon_url, save_url, time_post.strftime("%Y-%m-%d_%H-%M-%S"), title,
                            key]
            if save_url not in content_all.keys():
                log.debug("Adding URL to download list: %s", save_url)
                content_all[save_url] = content_list
    return content_all


def get_insta_post(url, name, driver=None,
                   write_file=True, file_path=default_filepath, file_name=default_filename,
                   driver_visible=True, driver_sleep=default_sleep, no_info=False):
    if not driver:
        options = webdriver.FirefoxOptions()
        options.headless = not driver_visible
        driver = webdriver.Firefox(options=options)
    try:
        driver.execute_script("window.open()")
        driver.switch_to.window(driver.window_handles[1])
        driver.get(url)
        time.sleep(driver_sleep)
        if driver.execute_script('return document.getElementsByClassName("JSZAJ  _3eoV-  IjCL9  WXPwG").length') == 0:
            content_count = 1
        else:
            content_count = driver.execute_script(
                'return document.getElementsByClassName("JSZAJ  _3eoV-  IjCL9  WXPwG")[0].childElementCount')
        content_all = {}
        log.info("Starting post downloader with original name: %s", name)
        log.debug("Got the following target URL: %s", url)
        log.debug("Number of downloads expected from this post: %s", content_count)
        if int(content_count) > 1:
            for i in range(content_count - 1):
                try:
                    driver.execute_script('document.getElementsByClassName("  _6CZji ")[0].click()')
                except Exception as e:
                    log.exception("Could not click next button. The following exception occurred: %s", e)
                time.sleep(driver_sleep)
                content_all = get_content(driver, name)
        else:
            content_all = get_content(driver, name)
        if not write_file:
            driver.execute_script("window.close()")
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(driver_sleep)
            return content_all
        for saves in content_all.keys():
            log.debug("Now working on: %s", content_all[saves][2])
            name = content_all[saves][0]
            icon_url = content_all[saves][1]
            save_url = content_all[saves][2]
            time_post = content_all[saves][3]
            title = content_all[saves][4]
            key = content_all[saves][5]
            result_list = [name, main_url[0], icon_url, time_post, title, key, url, save_url]
            file_title = title
            file_profile = name
            for badchar in replace_badfilename.keys():
                file_title = file_title.replace(badchar, replace_badfilename[badchar])
                file_profile = file_profile.replace(badchar, replace_badfilename[badchar])
            local_filename, headers = urllib.request.urlretrieve(save_url)
            save_file_path = file_path.replace("%title%", file_title) \
                .replace("%upload_date%", time_post) \
                .replace("%profile%", file_profile)
            save_file_name = file_name.replace("%title%", file_title) \
                .replace("%upload_date%", time_post) \
                .replace("%profile%", file_profile)
            if key == "images":
                file_ext = ".jpg"
            elif key == "videos":
                file_ext = ".mp4"
            else:
                file_ext = ""
            save_file_name = save_file_name + file_ext
            os.makedirs(save_file_path, exist_ok=True)
            full_path = os.path.normpath(save_file_path + "/" + save_file_name)
            content_all[saves].append(full_path)
            shutil.move(local_filename, full_path)
            if not no_info:
                info_dict = {"name": result_list[0], "insta_main_url": result_list[1],
                             "profile_icon_url": result_list[2], "post_time": result_list[3],
                             "description": result_list[4], "download_key": result_list[5],
                             "post_url": result_list[6], "download_url": result_list[7]}
                write_json(full_path + ".info", info_dict)
        driver.execute_script("window.close()")
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(driver_sleep)
        return content_all
    except Exception as e:
        log.exception("Downloading Insta post failed. The following exception occurred: %s", e)
        return None


def check_profile_url(url, driver, no_login=False, driver_sleep=default_sleep):
    try:
        if url.startswith(main_url[0]) or url.startswith(main_url[1]):
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
                log.error("Page seems to be broken. URL: %s", url)
            return return_list
        else:
            log.critical("Not an Instagram URL! Did someone change the file? "
                         "Shutting down to prevent further damage.")
            exit(2)
    except selenium.common.exceptions.WebDriverException as e:
        log.warning("Profile does not exist: %s", url)
        try:
            driver.quit()
        except Exception:
            pass
        return "404"
    except Exception as e:
        log.exception("Checking profile failed. The following exception occurred: %s", e)
        return None


def download_profile_url(url, name, driver, no_login=False, driver_sleep=default_sleep,
                         file_path=default_filepath, file_name=default_filename, write_file=True, no_info=False,
                         driver_visible=False):
    try:
        if url.startswith(main_url[0]) or url.startswith(main_url[1]):
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
                            result = get_insta_post(post_url, name, driver=driver, write_file=write_file,
                                                    file_path=file_path, file_name=file_name,
                                                    driver_visible=driver_visible,
                                                    driver_sleep=driver_sleep, no_info=no_info)
                            if result is not None:
                                return_dict[post_url] = result
                            else:
                                log.error("Crash in get_insta_post detected. Exiting...")
                                return None
                else:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.quit()
            if not one_left:
                log.error("Page seems to be broken. URL: %s", url)
            return return_dict
        else:
            log.critical("Not an Instagram URL! Did someone change the file? "
                         "Shutting down to prevent further damage.")
            exit(2)
    except selenium.common.exceptions.WebDriverException as e:
        log.warning("Profile does not exist: %s", url)
        try:
            driver.quit()
        except Exception:
            pass
        return "404"
    except Exception as e:
        log.exception("Could not download profile. The following exception occurred: %s", e)
        return None


cwd = os.getcwd()
default_infopath = cwd
default_infoname = "insta_info-"
os.chdir(Path(__file__).parent.absolute())

# noinspection PyTypeChecker
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

if args.verbose is not None:
    visible = args.verbose >= 3
    debug_file = args.verbose >= 2
    debug_output = args.verbose >= 1
else:
    visible = False
    debug_file = False
    debug_output = False

log = logging.getLogger("Insta-Downloader")
log.setLevel(logging.DEBUG)
log_format = logging.Formatter("%(asctime)s [%(levelname)s] (%(funcName)s): %(message)s")
log_stream = logging.StreamHandler()
log_stream.setFormatter(log_format)
log_file = logging.handlers.RotatingFileHandler(filename=config_logfile, mode="a",
                                                maxBytes=10000000, backupCount=3)
log_file.setFormatter(log_format)
log_file.setLevel(logging.DEBUG)
log.addHandler(log_file)

if debug_output:
    # noinspection PyArgumentList
    log_stream.setLevel(logging.DEBUG if debug_file else logging.INFO)
else:
    # noinspection PyArgumentList
    log_stream.setLevel(logging.ERROR)

log.addHandler(log_stream)

history_fullpath = args.history_path + "/" + config_history
os.makedirs(args.history_path, exist_ok=True)

log.info("Starting insta-downloader.py...")
log.debug("Starting to process args now.")

if args.progress_file:
    if debug_output:
        if os.path.isfile(default_progressfile):
            log.info("Waiting until in_progress file is removed...")
    while os.path.isfile(default_progressfile):
        time.sleep(1)
    log.debug("Writing in_progress file.")
    with open(default_progressfile, "w") as file:
        file.write("")
    log.info("Starting execution now.")

if args.all:
    log.info("Downloading every post of the provided profiles...")
    for profile_num in range(len(args.profiles)):
        profile = args.profiles[profile_num]
        log.info("Now working on profile: %s", profile)
        if profile.startswith(main_url[0]) or profile.startswith(main_url[1]):
            log.info("Profile is a valid Instagram URL.")
            log.info("Starting download process with Firefox.")
            profile_name = profile.split("/")[3]
            profile_driver = driver_startup(driver_visible=visible,
                                            disable_login=args.no_login,
                                            driver_sleep=args.sleep,
                                            use_creds=args.creds)
            if profile_driver is not None:
                profile_dict = download_profile_url(profile, profile_name, profile_driver,
                                                    no_login=args.no_login, driver_sleep=args.sleep,
                                                    file_path=args.filepath, file_name=args.filename,
                                                    no_info=args.no_info, write_file=not args.json,
                                                    driver_visible=visible)
                log.info("Finished download process.")
            else:
                log.critical("Could not finish driver_startup.")
                profile_dict = None
            history = load_json(history_fullpath)
            if profile_dict is not None and profile_dict != "404":
                history[profile_name] = profile_dict
                write_json(history_fullpath, history)
            elif profile_dict == "404":
                log.warning("Profile not found.")
                continue
            else:
                log.error("Download_profile_URL with profile: %s failed.", profile)
                if args.progress_file:
                    log.debug("Removing in_progress file...")
                    os.remove(default_progressfile)
                exit(1)
            json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
            if args.json and args.json_filename != "":
                log.debug("Creating json_file...")
                info_profile({profile_name: profile_dict}, filename=json_path)
            elif args.json and args.json_filename == "":
                log.debug("Creating json output...")
                info_profile({profile_name: profile_dict}, filename=json_path)
        else:
            profile = os.path.normpath(cwd + "/" + profile)
            log.info("Assuming profile is a file: %s", profile)
            try:
                with open(profile, "r") as file:
                    text = [x.replace("\n", "") for x in file.readlines()]
            except FileNotFoundError:
                log.error("The following file does not exist: %s", profile)
                text = []
            for line in text:
                if line.startswith(main_url[0]) or line.startswith(main_url[1]):
                    log.info("Working on URL of file: %s", line)
                    log.info("Starting download process with Firefox.")
                    profile_name = line.split("/")[3]
                    profile_driver = driver_startup(driver_visible=visible,
                                                    disable_login=args.no_login,
                                                    driver_sleep=args.sleep,
                                                    use_creds=args.creds)
                    if profile_driver is not None:
                        profile_dict = download_profile_url(line, profile_name, profile_driver,
                                                            no_login=args.no_login, driver_sleep=args.sleep,
                                                            file_path=args.filepath, file_name=args.filename,
                                                            no_info=args.no_info, write_file=not args.json,
                                                            driver_visible=visible)
                        log.info("Finished download process.")
                    else:
                        log.critical("Could not finish driver_startup.")
                        profile_dict = None

                    history = load_json(history_fullpath)
                    if profile_dict is not None and profile_dict != "404":
                        history[profile_name] = profile_dict
                    elif profile_dict == "404":
                        log.warning("Profile not found. Editing file...")
                        newtext = text.copy()
                        newtext.remove(line)
                        os.remove(profile)
                        with open(profile, "w") as newfile:
                            for x in newtext:
                                newfile.write(x + "\n")
                        log.debug("New file created.")
                        continue
                    else:
                        log.error("Download_profile_URL failed.")
                        if args.progress_file:
                            log.debug("Removing in_progress file...")
                            os.remove(default_progressfile)
                        exit(1)
                    write_json(history_fullpath, history)
                    json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
                    if args.json and args.json_filename != "":
                        log.debug("Creating json_file...")
                        info_profile({profile_name: profile_dict}, filename=json_path)
                    elif args.json and args.json_filename == "":
                        log.debug("Creating json output...")
                        info_profile({profile_name: profile_dict}, filename=json_path)
                else:
                    log.warning("Ignoring wrong URL. File: '%s' Line: '%s'", profile, line)
            if args.remove_profile:
                try:
                    log.debug("Removing profile...")
                    os.remove(profile)
                    if profile_num != 0:
                        profile_num -= 1
                except FileNotFoundError:
                    log.warning("Could not remove profile. File not found: %s", profile)
elif args.update:
    log.info("Downloading only recent posts of the provided profiles...")
    for profile_num in range(len(args.profiles)):
        profile = args.profiles[profile_num]
        log.info("Now working on profile: %s", profile)
        if profile.startswith(main_url[0]) or profile.startswith(main_url[1]):
            log.info("Profile is a valid Instagram URL.")
            log.info("Starting download process with Firefox...")
            profile_name = profile.split("/")[3]
            profile_driver = driver_startup(driver_visible=visible,
                                            disable_login=args.no_login,
                                            driver_sleep=args.sleep,
                                            use_creds=args.creds)
            if profile_driver is not None:
                profile_list = check_profile_url(profile, profile_driver,
                                                 no_login=args.no_login, driver_sleep=args.sleep)
                log.info("Finished download process.")
            else:
                log.critical("Could not finish driver_startup.")
                profile_list = None

            if profile_list is not None and profile_list != "404":
                profile_dict = update_profile(profile_driver, history_fullpath, profile_name, profile_list)
            elif profile_list == "404":
                log.warning("Profile not found.")
                continue
            else:
                profile_dict = None
            if profile_dict is None:
                if args.progress_file:
                    log.debug("Removing in_progress file...")
                    os.remove(default_progressfile)
                exit(1)
            json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
            if args.json and args.json_filename != "":
                log.debug("Creating json_file...")
                info_profile({profile_name: profile_dict}, filename=json_path)
            elif args.json and args.json_filename == "":
                log.debug("Creating json output...")
                info_profile({profile_name: profile_dict}, filename=json_path)
        else:
            profile = os.path.normpath(cwd + "/" + profile)
            log.info("Assuming profile is a file: %s", profile)
            try:
                with open(profile, "r") as file:
                    text = [x.replace("\n", "") for x in file.readlines()]
            except FileNotFoundError:
                log.error("The following file does not exist:", profile)
                text = []
            for line in text:
                if line.startswith(main_url[0]) or line.startswith(main_url[1]):
                    log.info("Working on URL of file: %s", line)
                    log.info("Starting download process with Firefox...")
                    profile_name = line.split("/")[3]
                    profile_driver = driver_startup(driver_visible=visible,
                                                    disable_login=args.no_login,
                                                    driver_sleep=args.sleep,
                                                    use_creds=args.creds)
                    if profile_driver is not None:
                        profile_list = check_profile_url(line, profile_driver,
                                                         no_login=args.no_login, driver_sleep=args.sleep)
                        log.info("Finished download process.")
                    else:
                        log.critical("Could not finish driver_startup.")
                        profile_list = None
                    if profile_list is not None and profile_list != "404":
                        profile_dict = update_profile(profile_driver, history_fullpath, profile_name, profile_list)
                        log.info("Finished update process.")
                    elif profile_list == "404":
                        log.warning("Profile not found. Editing file...")
                        newtext = text.copy()
                        newtext.remove(line)
                        os.remove(profile)
                        with open(profile, "w") as newfile:
                            for x in newtext:
                                newfile.write(x + "\n")
                        log.debug("New file created.")
                        continue
                    else:
                        profile_dict = None
                    if profile_dict is None:
                        if args.progress_file:
                            log.debug("Removing in_progress file...")
                            os.remove(default_progressfile)
                        exit(1)
                    json_path = os.path.normpath(args.json_path + "/" + args.json_filename)
                    if args.json and args.json_filename != "":
                        log.debug("Creating json_file...")
                        info_profile({profile_name: profile_dict}, filename=json_path)
                    elif args.json and args.json_filename == "":
                        log.debug("Starting to create json output...")
                        info_profile({profile_name: profile_dict}, filename=json_path)
                else:
                    log.warning("Ignoring wrong URL. File: '%s' Line: '%s'", profile, line)
            if args.remove_profile:
                try:
                    log.debug("Removing profile...")
                    os.remove(profile)
                    if profile_num != 0:
                        profile_num -= 1
                except FileNotFoundError:
                    log.warning("Could not remove profile. File not found: %s", profile)

if args.progress_file:
    log.debug("Removing in_progress file...")
    os.remove(default_progressfile)

log.info("Stopping insta-downloader.py...")
