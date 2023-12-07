#!/usr/bin/env python3

import yaml
import re
import time
from selenium import webdriver
import json
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
from pytz import timezone
import pytz
from playsound import playsound


def yaml_loader(filepath):
    # Loads yaml file
    with open(filepath, "r") as file_descriptor:
        data = yaml.load(file_descriptor)
    return data


# Sign-in Method
def site_login(driver, url, username, password):
    # driver.set_page_load_timeout(90)
    driver.get(url=url)
    time.sleep(2)
    if username == account["username"] and password == account["password"]:
        try:
            u_name = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, 'avatarname')))
            u_name.send_keys(username)
            u_password = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, 'password')))
            u_password.send_keys(password)
            driver.find_element_by_xpath('//*[@id="imvu"]/section[2]/div/div/div/section/form/div[4]/button').click()
            time.sleep(3)
        except TimeoutException:
            site_login(driver, url, username, password)


# Sets online status to configuration file's status value
def set_online_status(driver, online_status):
    profile_img = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "is-portrait")))
    profile_img.click()
    time.sleep(3)
    try:
        status = driver.find_element_by_id("profile-checkbox-show-online-status")
    except NoSuchElementException:
        profile_img.click()
        time.sleep(3)
        status = driver.find_element_by_id("profile-checkbox-show-online-status")
    if not online_status:
        if status.is_selected():
            print("Online status was: " + str(status.is_selected()))
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="imvu"]/nav/div[2]/div/div/div[1]/ul[1]/li[3]/label'))).click()
            print("Online status is now: " + str(status.is_selected()))
    if online_status:
        if not status.is_selected():
            print("Online status was: " + str(status.is_selected()))
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="imvu"]/nav/div[2]/div/div/div[1]/ul[1]/li[3]/label'))).click()
            print("Online status is now: " + str(status.is_selected()))
    print("Successfully logged in. Online status is " + str(online_status))
    print("-------------------------")
    time.sleep(1)


def get_user_cid(api_link):
    with requests.get(api_link) as response:
        data = json.loads(response.text)
        data = data["denormalized"][api_link]["data"]["items"]
        users = []
        [users.append(re.findall(r"(?<=user-)(\d+)", user)[0]) for user in data]
    return users


def days_to_secs(days):
    return days * 86400


# Create user api link
# Full api link created and stored in user_api_url_array
def create_user_api_urls(cid_array, max_cid_in_url):
    user_api_prof_url = 'https://api.imvu.com/user/user-'
    user_api_init_url = 'https://api.imvu.com/user?id='
    user_api_url_array = []
    temp_url = ''
    i = 1
    for cid in cid_array:
        temp_url += user_api_prof_url + str(cid)

        if i != max_cid_in_url and cid != cid_array[-1]:
            temp_url += ','

        if i == max_cid_in_url or cid == cid_array[-1]:
            user_api_url_array.append(user_api_init_url + temp_url)
            temp_url = ''
            i = 0

        i += 1

    return user_api_url_array


# Put all the cid's which meet the requirements into the
# validated_cid_array
def get_validated_cids(user_api_url_array):
    validated_cid_array = []
    curr_time = time.time()
    for user_api_url in user_api_url_array:
        json_data = json.loads(requests.get(user_api_url).text)

        for user_url, user_data in json_data['denormalized'].items():

            # Checks to see if the data is a user, otherwise skip them
            try:
                user_data['data']['legacy_cid']
            except KeyError:
                continue

            # See if cid meets account age requirements
            try:
                if ((curr_time - user_data["data"]["registered"]) < imvu_next['older_than']):
                    continue
            except KeyError:
                continue

            # Check to see if user has VIP if user_has_vip is enabled
            if imvu_next['user_has_vip']:
                try:
                    if (not user_data["data"]["is_vip"]):
                        continue
                except KeyError:
                    continue

            # Check to see if user has AP if user_has_ap is enabled
            if imvu_next['user_has_ap']:
                try:
                    if (not user_data["data"]["is_ap"]):
                        continue
                except KeyError:
                    continue

            # Check to see if user has age verification if user_has_age_verification is enabled
            if imvu_next['user_has_age_verification']:
                try:
                    if (not user_data["data"]["is_ageverified"]):
                        continue
                except KeyError:
                    continue

            # Check to see if user has AP if user_has_ap is enabled
            if imvu_next['user_has_marriage']:
                try:
                    if (user_data["relations"]["spouse"] != ""):
                        continue
                except KeyError:
                    continue

            # Check and validate gender
            if imvu_next['user_gender_mode'] == 0:
                try:
                    if (user_data["data"]["gender"] != "m"):
                        continue
                except KeyError:
                    continue
            elif imvu_next['user_gender_mode'] == 1:
                try:
                    if (user_data["data"]["gender"] != "f"):
                        continue
                except KeyError:
                    continue
            elif imvu_next['user_gender_mode'] == 2:
                try:
                    if (not user_data["data"]["gender"]):
                        continue
                except KeyError:
                    continue

            # If we reached here, the user has been validated
            validated_cid_array.append(user_data['data']['legacy_cid'])

    return validated_cid_array


def imvu_next_operation():
    if imvu_next["enable"]:
        driver.get("https://secure.imvu.com/next/feed/explore/")
        time.sleep(3)
        no_posts_wait = 10  # 10
        no_posts_attempt = 0
        post_num = 0
        num_posts = len(driver.find_elements_by_class_name("feed-item"))
        while num_posts <= 0:
            if no_posts_attempt >= 5:
                print("Couldn't find posts on IMVU next")
                exit()
            time.sleep(no_posts_wait)
            driver.get("https://secure.imvu.com/next/feed/explore/")
            no_posts_wait += 10
            no_posts_attempt += 1
            num_posts = len(driver.find_elements_by_class_name("feed-item"))
        # Finding the post to get users from
        if len(driver.find_elements_by_class_name("feed-item")) > 5:
            post_num = 0
        soup = BeautifulSoup(driver.page_source, "lxml")
        post = soup.find_all('article', {'class': 'feed-item'})[post_num]
        post_link = post['data-item']
        likes = post.footer.a.text
        print("LIKES: ", str(likes))
        number = re.findall(r"(\d+\.\d+|\d+)", likes)
        letter = re.findall(r"(\D+)(?= L)", likes)
        if len(number) > 0:
            print("LIKES: ", str(number[0]))
            number = float(number[0])
        if len(letter) > 0:
            print("LIKES LETTER: ", str(letter[0]))
            letter = str(letter[0])
            num = switch_letter(letter)
            like_counter = int(num * number)
            print("POST LIKES: " + str(like_counter))
            post_likes = int(like_counter)
        else:
            post_likes = int(number)
        html_element = driver.find_element_by_tag_name('html')
        while post_likes < imvu_next["amount"]:
            html_element.send_keys(Keys.END)
            post_num += 1
            soup = BeautifulSoup(driver.page_source, "lxml")
            post = soup.find_all('article', {'class': 'feed-item'})[post_num]
            post_link = post['data-item']
            likes = post.footer.a.text
            print("LIKES: ", str(likes))
            number = re.findall(r"(\d+\.\d+|\d+)", likes)
            letter = re.findall(r"(\D+)(?= L)", likes)
            if len(number) > 0:
                print("LIKES: ", str(number[0]))
                number = float(number[0])
            if len(letter) > 0:
                print("LIKES LETTER: ", str(letter[0]))
                letter = str(letter[0])
                num = switch_letter(letter)
                like_counter = int(num * number)
                print("POST LIKES: " + str(like_counter))
                post_likes = int(like_counter)
            else:
                post_likes = int(number)
        print('************** LINK FOR THIS POST **************', post_link)
        api_extension = '/liked_by_profile?limit=' + str(post_likes)
        api_link = post_link + api_extension
        print('************** API-LINK FOR THIS POST **************', api_link)
        user_cid_array = get_user_cid(api_link)
        print('************** USER CIDs: %s **************' % str(len(user_cid_array)))
        # cid_array should have all the users cid who liked the post
        user_api_url_array = create_user_api_urls(user_cid_array, 100)
        print('************** USER APIs: %s **************' % str(len(user_api_url_array)))
        validated_cid_array = get_validated_cids(user_api_url_array)
        print('************** VALIDATED CIDs: %s **************' % str(len(validated_cid_array)))
        url = "https://secure.imvu.com/next/av/user-"
        amount_added = 0
        user_row = -1
        if len(validated_cid_array) >= imvu_next["amount"]:
            valid_cids = imvu_next["amount"]
        else:
            valid_cids = len(validated_cid_array) - 1
        print('************** FINAL VALID CIDs: %s **************' % str(valid_cids))
        while amount_added < valid_cids:
            print('************** AMOUNT ADDED: %s **************' % str(amount_added))
            user_row += 1
            driver.get(url + str(validated_cid_array[user_row]))
            print('************** USER ROW %d **************' % user_row)
            time.sleep(imvu_next["delay_between_adds"])
            if imvu_next["add_mode"] == 0:
                try:
                    driver.find_element_by_class_name('icon-action_more_new').click()
                    time.sleep(1)
                    elem = driver.find_element_by_xpath('/html/body/section/ul/li[2]')
                    if elem.is_enabled() and elem.text == "Add Friend":
                        try:
                            elem.click()
                        except:
                            pass
                        print('************** USER ADDED AS A: FRIEND **************')
                        amount_added += 1
                except TimeoutException:
                    continue

            elif imvu_next["add_mode"] == 1:
                try:
                    container_follow = driver.find_element_by_class_name('follow-container')
                    btn_f = container_follow.find_element_by_css_selector('.follow-button.btn-simple')
                    if btn_f.text == "FOLLOW":
                        container_follow.click()
                        print('************** USER FOLLOWING **************')
                    amount_added += 1
                except TimeoutException:
                    continue
                except NoSuchElementException:
                    continue
            else:
                try:
                    driver.find_element_by_class_name('icon-action_more_new').click()
                    time.sleep(1)
                    elem = driver.find_element_by_xpath('/html/body/section/ul/li[2]')
                    if elem.is_enabled() and elem.text == "Add Friend":
                        try:
                            elem.click()
                        except:
                            pass
                        print('************** USER ADDED AS A: FRIEND **************')
                    try:
                        container_follow = driver.find_element_by_class_name('follow-container')
                        btn_f = container_follow.find_element_by_css_selector('.follow-button.btn-simple')
                        print('************** BUTTON FOLLOW STATUS: %s **************' % btn_f.text)
                        if btn_f.text == "FOLLOW":
                            container_follow.click()
                            print('************** USER FOLLOWING **************')
                    except NoSuchElementException:
                        pass
                    except TimeoutException:
                        pass
                except NoSuchElementException:
                    pass
                except TimeoutException:
                    pass
                amount_added += 1
        if overall["enable-classic-redirect"]:
            driver.get("https://secure.imvu.com/switch_to/classic/")
        time.sleep(imvu_next["delay_after_process"])
        print("Successfully added " + str(amount_added) + " people using IMVU Next at", datetime.now())


def people_search_operation():
    if people_search["enable"]:
        page_num = 15
        amount_added = 0
        while page_num != 0:
            url = people_search["url"] + "&page=" + str(page_num)
            try:
                driver.get(url)
                time.sleep(3)
            except TimeoutException:
                driver.get(url)
                time.sleep(5)
            print('************** PROCESSING PAGE: %d **************' % page_num)
            try:
                amount_of_users = WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CLASS_NAME, 'thumb')))
            except TimeoutException:
                amount_of_users = driver.find_elements_by_class_name('thumb')
            page_adds = 0
            user_num = 0
            while page_adds < len(amount_of_users):
                time.sleep(5)
                # using the JavaScriptExecutor to scroll down window by number in y-axis
                # driver.execute_script("window.scrollTo(0, 100);")
                icons = \
                    WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'icons')))[
                        user_num]
                icons.find_elements_by_tag_name('a')[2].click()
                user_num += 1
                time.sleep(people_search["delay_between_adds"])
                try:
                    bd = driver.find_element_by_class_name('bd')
                    msg = bd.find_element_by_class_name('msg').text
                    msg1 = re.findall(r"(\D+)(?= sent)", msg)
                    msg2 = re.findall(r"(\D{12})(?=your friend!)", msg)
                    if msg1 == "A friend request has been":
                        print('************** A FRIEND REQUEST HAS BEEN SENT **************')
                        amount_added += 1
                        bd.find_element_by_id('imvu-ok-message-okbutton').click()
                    elif msg2 == " is already ":
                        print('************** USER IS ALREADY YOUR FRIEND **************')
                        bd.find_element_by_id('imvu-ok-message-okbutton').click()
                    else:
                        bd.find_element_by_id('imvu-ok-message-okbutton').click()
                    page_adds += 1
                except:
                    try:
                        bd = driver.find_element_by_class_name('bd')
                        bd.find_element_by_id('imvu-ok-message-okbutton').click()
                    except:
                        pass

                print('************** DONE WITH USER %d **************' % page_adds)
            print('************** DONE WITH PAGE: %d **************' % page_num)
            page_num -= 1
        time.sleep(people_search["delay_after_process"])
        print("Successfully added " + str(amount_added) + " Using Find People at ", datetime.now())


def unfollow_operation():
    if unfollow["enable"]:
        driver.get("https://secure.imvu.com/next/friends/following/")
        time.sleep(3)
        html_element = driver.find_element_by_tag_name('html')
        following_count = int(driver.find_element_by_class_name('following-count').text)
        print('************** FOLLOWING COUNT: %d **************' % following_count)
        articles = driver.find_elements_by_class_name('profile-list-item')
        follows = len(articles)
        while follows < following_count:
            html_element.send_keys(Keys.END)
            time.sleep(5)
            articles = driver.find_elements_by_class_name('profile-list-item')
            follows = len(articles)
        html_element.send_keys(Keys.UP)
        user_list = []
        with open("whitelist.txt", 'r+') as f:
            for line in f:
                user_list.append(line.strip())
            f.close()
        articles = driver.find_elements_by_class_name('profile-list-item')
        follows = len(articles)
        print('************** FOLLOWING USERS: %d **************' % follows)
        i = 0
        skipped = 0
        for follow in range(following_count):
            html_element.send_keys(Keys.UP)
            article = driver.find_elements_by_class_name('profile-list-item')[i]
            print('************** SELECTED USER: **************', i)
            user = article.find_element_by_css_selector('.at-avatar-name-text.is-truncated').text
            print('************** FOLLOW USER NAME: **************', user)
            i += 1
            if i > 5:
                i = skipped
            if user in user_list:
                print('************** USER FOUND IN WHITELIST: **************', user)
                skipped += 1
                continue
            else:
                if unfollow["unfollow_mode"] == 0:
                    article.find_element_by_tag_name('dual-name-icon').click()
                    time.sleep(3)
                    driver.find_element_by_class_name('action-more-container').find_element_by_tag_name(
                        'button').click()
                    time.sleep(1)
                    context_menu = driver.find_element_by_class_name('context-menu')
                    time.sleep(1)
                    btn_unfriend = context_menu.find_elements_by_tag_name('li')[1]
                    if btn_unfriend.is_enabled() and btn_unfriend.text == "Unfriend":
                        btn_unfriend.click()
                        time.sleep(1)
                        driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[
                            1].click()
                        time.sleep(3)
                        driver.find_element_by_class_name('dialog-footer').find_element_by_tag_name('button').click()
                        print('************** YOU JUST UNFRIEND USER: %s **************' % str(user))
                    WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                        (By.XPATH, '//*[@id="imvu"]/section[2]/div/div[2]/div/a[1]'))).click()
                elif unfollow["unfollow_mode"] == 1:
                    try:
                        article.find_element_by_class_name('following-txt').click()
                        time.sleep(3)
                        driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[
                            1].click()
                        print('************** YOU JUST UNFOLLOWED USER: %s **************' % str(user))
                        time.sleep(3)
                    except NoSuchElementException:
                        time.sleep(1)
                        driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[
                            1].click()
                        print('************** YOU JUST UNFOLLOWED USER: %s **************' % str(user))
                        time.sleep(1)
                    except WebDriverException:
                        continue
                else:
                    try:
                        article.find_element_by_tag_name('dual-name-icon').click()
                        time.sleep(3)
                        driver.find_element_by_class_name('action-more-container').click()
                        btn_unf = driver.find_element_by_class_name('context-menu')
                        btn_unf = btn_unf.find_elements_by_tag_name('li')[1]
                        if btn_unf.is_enabled() and btn_unf.text == "Unfriend":
                            btn_unf.click()
                            time.sleep(1)
                            driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[
                                1].click()
                            time.sleep(1)
                            driver.find_element_by_class_name('dialog-footer').find_element_by_tag_name('button').click()
                        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                            (By.XPATH, '//*[@id="imvu"]/section[2]/div/div[2]/div/a[1]'))).click()
                        article.find_element_by_tag_name('button').click()
                        driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[1].click()
                        print('************** YOU JUST UNFOLLOWED AND UNFRIEND USER: %s **************' % str(user))
                        html_element.send_keys(Keys.UP)
                        time.sleep(1)
                    except NoSuchElementException:
                        time.sleep(1)
                        article.find_element_by_tag_name('dual-name-icon').click()
                        time.sleep(3)
                        driver.find_element_by_class_name('action-more-container').click()
                        btn_unf = driver.find_element_by_class_name('context-menu')
                        btn_unf = btn_unf.find_elements_by_tag_name('li')[1]
                        if btn_unf.is_enabled() and btn_unf.text == "Unfriend":
                            btn_unf.click()
                            time.sleep(1)
                            driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[
                                1].click()
                            time.sleep(1)
                            driver.find_element_by_class_name('dialog-footer').find_element_by_tag_name(
                                'button').click()
                        WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                            (By.XPATH, '//*[@id="imvu"]/section[2]/div/div[2]/div/a[1]'))).click()
                        article.find_element_by_tag_name('button').click()
                        driver.find_element_by_class_name('dialog-footer').find_elements_by_tag_name('button')[
                            1].click()
                        print('************** YOU JUST UNFOLLOWED AND UNFRIEND USER: %s **************' % str(user))
                        html_element.send_keys(Keys.UP)
                        time.sleep(1)
                    except WebDriverException:
                        continue
        if overall["enable-classic-redirect"]:
            driver.get("https://secure.imvu.com/switch_to/classic/")
        time.sleep(unfollow["delay_after_process"])


def switch_letter(x):
    return {
        'K': 1000,
        'M': 1000000,
    }.get(x, 1)


def get_pacific_time():
    date_format = '%m/%d/%Y'
    date = datetime.now(tz=pytz.utc)
    date.strftime(date_format)
    date = date.astimezone(timezone('US/Pacific'))
    return datetime.strptime(date.strftime(date_format), date_format)


def logout():
    driver.get("https://www.imvu.com/catalog/logoff.php")
    print('************** YOU HAVE SUCCESSFULLY LOGGED OUT **************')
    exit()


def launch_operations():
    times_executed = 0
    print('***** Press CTRL+c to quit *****')
    while True:
        try:
            # imvu_next_operation()
            # people_search_operation()
            unfollow_operation()
            """ A 30 minutes wait """
            time.sleep(1800)
            print("-------------------------")
            times_executed += 1
            print('************** TIMES EXECUTED: %d **************' % times_executed)
        except (KeyboardInterrupt, SystemExit):
            logout()


# ***************************************************************
#    The program starts from here
# ***************************************************************
config = yaml_loader("config.yml")
account = config.get("account")
overall = config.get("overall")
imvu_next = config.get("imvu_next")
people_search = config.get("people_search")
unfollow = config.get("unfollow")
login_url = "https://secure.imvu.com/welcome/login/"
options = webdriver.ChromeOptions()
options.add_argument("--incognito")
driver = webdriver.Chrome(options=options)
username = account["username"]
password = account["password"]
site_login(driver, login_url, username, password)
online_status = account["show_online_status"]
set_online_status(driver, online_status)
post_number = 0
launch_operations()
driver.get("https://www.imvu.com/catalog/logoff.php")
print("Finished")
if overall["play_finished_sound"]:
    playsound('finished_sound.mp3')
driver.quit()
