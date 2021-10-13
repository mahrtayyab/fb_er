import json
import logging
from urllib import parse
import bs4
import re

import cssutils
from bs4 import BeautifulSoup as bs
import hashlib
cssutils.log.setLevel(logging.CRITICAL)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 "
    "Safari/537.36 "
]
FB_DTSG_REGEX = re.compile(r'name="fb_dtsg" value="(.*?)"')


def get_group_graph_params(*args):
    params = {
        "av": args[0],
        "__user": args[0],
        "fb_dtsg": args[1],
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "MGroupsLandingYourGroupContentQuery",
        "variables": json.dumps(args[2]),
        "doc_id": "3059337350754217"
    }
    return params


def md5checksum(fname):
    md5 = hashlib.md5()

    # handle content in binary form
    f = open(fname, "rb")

    while chunk := f.read(4096):
        md5.update(chunk)

    return md5.hexdigest()


def get_user_id(session):
    rtn = session.cookies.get_dict().get("c_user")
    if rtn is None:
        rtn = str(session.headers).split("c_user")[1].strip()[1:-1]
        if rtn is None or rtn == "":
            return "Couldn't find"
    return str(rtn)


def is_home(url):
    parts = parse.urlparse(url)
    # Check the urls `/home.php` and `/`
    return "home" in parts.path or "/?_rdr" == parts.path or "/" == parts.path


def on2FACode(session, r):
    """Called when a 2FA code is needed to progress."""
    # soup = find_input_fields(r.text)
    data = dict()
    session.headers['referer'] = "https://m.facebook.com/checkpoint/"
    session.headers['accept-encoding'] = "gzip, deflate, br"
    session.headers['upgrade-insecure-requests'] = "1"
    session.headers['sec-ch-ua'] = '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"'
    session.headers['sec-fetch-user'] = "?1"
    r = session.get("https://m.facebook.com/login/checkpoint/?having_trouble=1")
    print("\r[-] Requesting Two Factor Authentication using SMS")
    url = "https://m.facebook.com/login/checkpoint/"

    data["fb_dtsg"] = \
        re.findall('\["MRequestConfig",\[],\{"dtsg":\{"token":"(.*?)","valid_for":(.*?),"expire":(.*?)}', r.text)[0][0]
    data["nh"] = bs4.BeautifulSoup(r.text, "html.parser").find("input", {"name": "nh"})["value"]
    data["submit[Continue]"] = "Continue"
    data["help_selected"] = "sms_requested"
    data["checkpoint_data"] = ""
    r = session.post(url, data=data)
    if "Enter login code to continue" in r.text or bs4.BeautifulSoup(r.text, "html.parser").find(
            "title").text == "Enter login code to continue":
        code = input("Please enter your 2FA code --> ")
        return code, r
    else:
        print(r.text)
        print("""[!] Couldn't Request Two Factor Authentication using SMS
    Please Make Sure you have a mobile number connected to the Facebook Account
""")
        exit(1)


def two_fa_helper(session, code, r):
    soup = find_input_fields(r.text)
    data = dict()

    url = "https://m.facebook.com/login/checkpoint/"

    data["approvals_code"] = code
    data["fb_dtsg"] = soup.find("input", {"name": "fb_dtsg"})["value"]
    data["nh"] = soup.find("input", {"name": "nh"})["value"]
    data["submit[Submit Code]"] = "Submit Code"
    data["codes_submitted"] = 0
    # print(data)
    r = session.post(url, data=data)

    if is_home(r.url):
        return r

    del data["approvals_code"]
    del data["submit[Submit Code]"]
    del data["codes_submitted"]

    data["name_action_selected"] = "save_device"
    data["submit[Continue]"] = "Continue"
    # print(data)
    # At this stage, we have dtsg, nh, name_action_selected, submit[Continue]
    r = session.post(url, data=data)

    if is_home(r.url):
        return r

    del data["name_action_selected"]
    # At this stage, we have dtsg, nh, submit[Continue]
    r = session.post(url, data=data)

    if is_home(r.url):
        return r

    del data["submit[Continue]"]
    data["submit[This was me]"] = "This Was Me"
    # At this stage, we have dtsg, nh, submit[This was me]
    r = session.post(url, data=data)

    if is_home(r.url):
        return r

    del data["submit[This was me]"]
    data["submit[Continue]"] = "Continue"
    data["name_action_selected"] = "save_device"
    # At this stage, we have dtsg, nh, submit[Continue], name_action_selected
    r = session.post(url, data=data)
    return r


def find_input_fields(html):
    return bs4.BeautifulSoup(html, "html.parser", parse_only=bs4.SoupStrainer("input"))


def prefix_url(url):
    if url.startswith("/"):
        return "https://www.facebook.com" + url
    return url


def from_session(session):
    # TODO: Automatically set user_id when the cookie changes in the session
    tmp = get_user_id(session)
    user_id = tmp if tmp is not None else ""

    r = session.get(prefix_url("/"))

    soup = find_input_fields(r.text)
    fb_dtsg_element = soup.find("input", {"name": "fb_dtsg"})
    if fb_dtsg_element:
        fb_dtsg = fb_dtsg_element["value"]
    else:
        try:
            # Fall back to searching with a regex
            fb_dtsg = FB_DTSG_REGEX.search(r.text).group(1)
        except:
            fb_dtsg = re.findall('__comet_req=(.*?)","(.*?)","(.*?)",(.*?),"(.*?)"', r.text)[0][4]
    revision = int(r.text.split('"client_revision":', 1)[1].split(",", 1)[0])

    logout_h_element = soup.find("input", {"name": "h"})
    logout_h = logout_h_element["value"] if logout_h_element else None
    return {
        "user_id": user_id,
        "fb_dtsg": fb_dtsg,
        "revision": revision,
        "session": session,
        "logout_h": logout_h,
    }


def find_friends(r):
    friends = []
    fri = bs(r.content, "html.parser").find_all("div", {"class": "_55wp _7om2 _5pxa _8yo0"})
    for i in fri:
        name = i.find("h3", {"class": "_52jh _5pxc _8yo0"}).find("a").text.strip("\u200e")
        link = i.find("h3", {"class": "_52jh _5pxc _8yo0"}).find("a").get("href")
        if not str(link).startswith("/profile"):
            try:
                fb_username = link.split("?")[0] if "?" in link else link
            except TypeError:
                fb_username = None
        else:
            fb_username = None
        uid = eval(i.find("a", {"class": "touchable right _58x3"}).get("data-store"))['id']
        friends.append({"name": name, "uid": uid, "facebook_profile_url": f"https://facebook.com/{link}","fb_username":fb_username})
    try:
        nextURL = re.findall('href:"/(.*?)/friends\?unit_cursor=(.*?)"', r.text)[0]
    except IndexError:
        nextURL = ""
    return nextURL, friends


def find_birthdays(r, s=None):
    bds = {}
    if s is None:
        all_articles = bs(r.content, "html.parser").find_all("article", {"class": "_5oxw _55wr _5e4e"})
        for article in all_articles:
            # print(article)
            h4 = article.find("h4").text
            bds[h4] = list()
            if h4 == "Today's Birthdays":
                tmp = article.find("ul", {"class": "_5pkb _55x2 _55wp"}).find_all("div", {"class": "_55ws _2vyq"})
            else:
                tmp = article.find("div", {"class": "_55wo _55x2 _56bf"}).find("ul").find_all("li")
            for i in tmp:
                div_style = i.find("i")['style']

                style = cssutils.parseStyle(div_style)

                url = style['background']

                url = url.replace('url(', '').replace(')', '')[8:-17].replace("\\", "")
                tmpDict = {"name": i.find_all("a")[0].find_all("p")[0].text,
                           "birthday": i.find_all("a")[0].find_all("p")[1].text}
                bds[h4].append(tmpDict)
    else:
        all_articles = bs(r['html'].replace("\\", ""), "html.parser").find_all("article")
        for article in all_articles:
            # print(article)
            h4 = article.find("h1").text
            bds[h4] = list()
            if h4 == "Today's Birthdays":
                tmp = article.find("ul", {"class": "_5pkb _55x2 _55wp"}).find_all("div", {"class": "_55ws _2vyq"})
            else:
                tmp = article.find("div", {"class": "_55wo _55x2 _56bf"}).find("ul").find_all("li")
            for i in tmp:
                div_style = i.find("i")['style']
                style = cssutils.parseStyle(div_style)
                url = style['background']
                tmpDict = {"name": i.find_all("a")[0].find_all("p")[0].text,
                           "birthday": i.find_all("a")[0].find_all("p")[1].text}
                bds[h4].append(tmpDict)
    try:
        nextURL = re.findall('href:"/events/ajax/dashboard/calendar/birthdays/\?acontext=(.*?)"', r.text)[0]
    except IndexError:
        nextURL = ""
    except (AttributeError, KeyError):
        try:
            nextURL = re.findall('"href":"/events/ajax/dashboard/calendar/birthdays/\?acontext=(.*?)"',
                                 r['code'].replace("\\", ""))[0]
        except IndexError:
            nextURL = ""
    return nextURL, bds


def getNext(url, session, method=None):
    if method is None:
        return session.get(url)
    else:
        html = {}
        r = session.get(url)
        jk = r.text[9:].replace('false', 'False').replace('true', "True")
        evjk = eval(jk)
        html['html'] = str(evjk['payload']['actions'][0]['html'])
        html['code'] = str(evjk['payload']['actions'][2]['code'])
        return html


def identifier(s):
    if s.isdigit():
        typeof = "id"
    else:
        if len(s.split(" ")) == 1:
            typeof = "username"
        else:
            typeof = "name"
    return typeof


def find_specific_friend(typ, identity, friends):
    if typ == "id":
        for friend in friends['friends']:
            if friend['uid'] == identity:
                return friend
    elif typ == "username":
        for friend in friends['friends']:
            if identity in friend['facebook_profile_url']:
                return friend
    elif typ == "name":
        for friend in friends['friends']:
            if friend['name'] == identity:
                return friend
    return None


def graphql_query(session, params):
    r = session.post("https://m.facebook.com/api/graphql/", data=params)
    return r.json()

def parse_group(json_):
    pass