import os
import random
import string
import time
import traceback

from ics import Calendar, Event
import magic
import requests
from requests_toolbelt import MultipartEncoder
from ._util import *


def proxyFactory():
    # https://proxylist.geonode.com/api/organdasn?limit=200&page=2
    r = requests.get("https://free-proxy-list.net/")
    soup = bs(r.content, "html.parser")
    tds = soup.find("tbody").find_all("tr")
    proxies = []
    for i in tds:
        proxies.append(f"{i.find_all('td')[0].text}:{i.find_all('td')[1].text}")
    return proxies


def session_factory(user_agent=None, f=False, cookies=None, proxies=None):
    # Requesting a session with required Headers

    session = requests.session()
    session.headers["Referer"] = "https://m.facebook.com/"

    # Some headers broke the login system,
    # so using f parameter , trying a dirty way to eliminate those headers while logging in
    if f is False:
        session.headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp," \
                                    "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9 "
        session.headers['sec-fetch-mode'] = "navigate"
        session.headers['accept-encoding'] = "gzip, deflate, br"
        session.headers['upgrade-insecure-requests'] = "1"
        session.headers['cache-control'] = "max-age=0"
        session.headers['sec-ch-ua'] = '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"'
        session.headers['sec-fetch-user'] = "?1"

    # If user is logging in using cookies ,
    # adding those cookies to session headers, as facebook doesn't accepts cookies in cookie jar
    if cookies is not None:
        session.headers['cookie'] = ""
        if type(cookies) is str:
            session.headers['cookie'] = cookies
        else:
            for i in cookies.iteritems():
                session.headers['cookie'] = session.headers['cookie'] + f"{i[0]}={i[1]};"

    if proxies is not None:
        print(f'Adding Proxy {proxies} in session')
        session.proxies.update(proxies)
    # TODO: Deprecate setting the user agent manually
    session.headers["user-agent"] = user_agent if user_agent is not None else random.choice(USER_AGENTS)
    return session


class Facebook:
    def __init__(self, username=None, password=None, use_cookies=False, cookie=None, user_agent=None):
        """
        Init Method for using the Facebook Class, this is the parent class for all the functions
        The Class can be Initiated on two ways:
        1. by providing username/email/phone_number and password to your facebook account
        2. by using use_cookies=True and providing a cookie value

        Usage:
            Facebook(username="my_username",password=""password")
            Facebook(use_cookies=True,cookie="facebook_cookie_value")
        :param username: username of facebook account
        :param password: password of facebook account
        :param use_cookies: use cookies to log in
        :param cookie: cookie value if use_cookies=True
        :param user_agent: browser user agent
        """
        self.login_url = "https://m.facebook.com/login.php?login_attempt=1"
        self.username = username
        self.password = password
        self.user_agent = user_agent
        self.cookie = cookie
        self.logged_in = False
        self.user_Datagram = dict()
        self.use_cookies = use_cookies
        self.__login()

    def __login(self, user_agent=None):
        """
        Internal Login In method used for logging in to Facebook
        :param[Optional] user_agent: browser user agent
        """

        if self.use_cookies is False:
            if self.username and self.password:
                print(f"\r[-] Logging In using Username {self.username} and password *********", end="")
                session = session_factory(user_agent=user_agent, f=True)

                soup = find_input_fields(session.get("https://m.facebook.com/").text)
                data = dict(
                    (elem["name"], elem["value"])
                    for elem in soup
                    if elem.has_attr("value") and elem.has_attr("name")
                )
                data["email"] = self.username
                data["pass"] = self.password
                data["login"] = "Log In"

                r = session.post(self.login_url, data=data)
                # Usually, 'Checkpoint' will refer to 2FA
                if "https://m.facebook.com/checkpoint/" in r.url or r.url == "https://m.facebook.com/checkpoint/?_rdr" \
                        or r.url == "https://m.facebook.com/checkpoint/" or "checkpoint" in r.url.split("/") \
                        and ('id="approvals_code"' in str(r.content)):
                    print("\r[!] Two Factor Authentication Required", end="")
                    code, r = on2FACode(session, r)
                    r = two_fa_helper(session, code, r)
                # Sometimes Facebook tries to show the user a "Save Device" dialog
                if "save-device" in r.url:
                    r = session.get("https://m.facebook.com/login/save-device/cancel/")
                if "Error" in r.text:
                    r.url = "https://m.facebook.com/home.php"
                if is_home(r.url):
                    try:
                        name = re.findall('"NAME":"(.*?)"', r.text)[0]
                        print(f"\r[*] Successfully Logged in as {name}")
                    except:
                        print(r.text)
                        exit(1)
                    accountId = re.findall('"ACCOUNT_ID":"(.*?)"', r.text)[0]
                    dtsg = re.findall('"dtsg_ag":\{"token":"(.*?)","valid_for":(.*?),"expire":(.*?)}', r.text)[0][0]
                    di = from_session(session=session)
                    di['name'] = name
                    di['accountId'] = accountId
                    di['dtsg'] = dtsg
                    self.user_Datagram = di
                    self.logged_in = True
                    self.cookie = session.cookies
                    return di
                else:
                    raise ValueError("[!] Couldn't LogIn, Please Try again")
            else:
                raise ValueError("[!] Please Provide A username and Password to Login")
        else:
            if self.cookie is not None:
                print(f"[-] Logging In using Cookies", end="")
                session = session_factory(user_agent=user_agent, cookies=self.cookie)
                r = session.get("https://m.facebook.com")
                if is_home(r.url):
                    name = re.findall('"NAME":"(.*?)"', r.text)[0]
                    print(f"\r[*] Successfully Logged in as {name}")
                    accountId = re.findall('"ACCOUNT_ID":"(.*?)"', r.text)[0]
                    dtsg = re.findall('"dtsg_ag":\{"token":"(.*?)","valid_for":(.*?),"expire":(.*?)}', r.text)[0][0]
                    di = from_session(session=session)
                    di['name'] = name
                    di['accountId'] = accountId
                    di['dtsg'] = dtsg
                    self.user_Datagram = di
                    self.logged_in = True
                    # print(session.cookies)
                    return di
                else:
                    print("[!] Couldn't LogIn, Please Try again")
                    return 0
            else:
                raise ValueError("Please Provide cookies when using use_cookies=True")

    @staticmethod
    def __to_ics(resp,file_name,event_name_prefix=None):
        c = Calendar()
        if not event_name_prefix:
            event_name_suffix = "Birthday Of"
        for day in range(1,len(resp['birthdays'])):
            for k, v in resp['birthdays'][day].items():
                month = k
                for j in v:
                    name = j['name']
                    bd = j['birthday']
                    date_ = parse_bd(bd)
                    e = Event()
                    e.name = f"{event_name_suffix} {name}"
                    e.begin = f'{date_} 00:00:00'
                    c.events.add(e)
        with open(f"{file_name}.ics", 'w',errors="ignore") as my_file:
            my_file.writelines(c)

    def userinfo(self,user=None,timeline=None) -> dict:
        """

        :param user: user id of the user
        :param timeline: yet not implemented
        :return: dict
        :TODO : Get Timeline Items
        """
        if self.logged_in:
            session = session_factory(cookies=self.cookie)
            session.headers.pop('Referer')
            if user is None:
                r = session.get("https://m.facebook.com/profile.php")
                name = re.findall('"NAME":"(.*?)"', r.text)[0]
                accountId = re.findall('"ACCOUNT_ID":"(.*?)"', r.text)[0]
            else:
                r = session.get(f"https://m.facebook.com/profile.php?id={user}")
                name = re.findall('<title>(.*?)</title>', r.text)[0]
                accountId = re.findall('profile_id=(.*?)&', r.text)[0]
            try:
                total_friends = re.findall('<div class="_7-1j">(.*?)friends</div>', r.text)[0]
            except IndexError:
                total_friends = None
            try:
                seeMore = re.findall('href="/(.*?)/about\?lst=(.*?)&amp;refid=(.*?)', r.text)
                seeMore = seeMore[0]
            except IndexError:
                seeMore = None
            try:
                livesIn = re.findall('<div><span class="_7i5d">Lives in <strong><span class="unlinkedTextEntity">('
                                     '.*?)</span></strong></span></div>', r.text)[0]
            except IndexError:
                livesIn = None
            try:
                joinedOn = re.findall('<span class="_7i5d">Joined on (.*?)</span>', r.text)[0]
            except IndexError:
                joinedOn = None
            birth = None
            gender = None
            mbl = None
            insta = None
            email = None
            twitter = None
            snap = None
            linkedIn = None
            github = None
            skype = None
            web = None
            try:
                alt = re.findall('<span class="alternate_name">\((.*?)\)</span>',r.text)[0]
            except:
                alt = None
            if seeMore is not None:
                try:
                    p = session.get(f"https://m.facebook.com/{seeMore[0]}/about?lst={seeMore[1]}")
                except:
                    p = None
                try:
                    birth = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">Date of birth</span></div>', p.text)[0].split(">")[-1]
                except:
                    birth = None
                try:
                    gender = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd '
                                    '_52ja _52jg">Gender</span></div>', p.text)[0].split(">")[-1]
                except:
                    gender = None
                try:
                    mbl = re.findall('<div class="_5cdv r"><span class="_52jh touchable" data-sigil="touchable"><span '
                                 'dir="ltr">(.*?)</span></span></div><div class="_52ja _5ejs"><span class="_52jd '
                                 '_52ja _52jg">Mobile</span></div>', p.text)[0]
                except:
                    mbl = None
                try:
                    insta = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">Instagram</span></div>', p.text)[0].split(">")[-1]
                except:
                    insta = None
                try:
                    email = re.findall('<div class="_5cdv r"><a href="mailto:(.*?)" class="touchable _52jh" '
                                   'data-sigil="touchable">(.*?)</a></div><div class="_52ja _5ejs"><span class="_52jd '
                                   '_52ja _52jg">Email address</span></div>', p.text)[0][0].split(">")[-1].replace(
                    "%40", "@")
                except:
                    email = None
                try:
                    twitter = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">Twitter</span></div>', p.text)[0].split(">")[-1]
                except:
                    twitter = None
                try:
                    snap = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">Snapchat</span></div>', p.text)[0].split(">")[-1]
                except:
                    snap = None
                try:
                    linkedIn = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">LinkedIn</span></div>', p.text)[0].split(">")[-1]
                except:
                    linkedIn = None
                try:
                    github = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">GitHub</span></div>', p.text)[0].split(">")[-1]
                except:
                    github = None
                try:
                    skype = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">Skype</span></div>', p.text)[0].split(">")[-1]
                except:
                    skype = None
                try:
                    web = re.findall('<div class="_5cdv r">(.*?)</div><div class="_52ja _5ejs"><span class="_52jd _52ja '
                                   '_52jg">Websites</span></div>', p.text)[0].split(">")[-2][:-3]
                except:
                    web = None
            r_tmp = r.text.replace("<!--", "").replace("-->", "")
            bio = bs(r_tmp,"html.parser").find("div",{"id":"bio"}).text
            user = {
                "name": {
                    "name":name,
                    "alternative_name":alt
                },
                "bio":bio,
                "AccountId": accountId,
                "total_friends": total_friends,
                "livesIn": livesIn,
                "joinedOn": joinedOn,
                "dateOfBirth": birth,
                "gender": gender,
                "contact_details": {
                    "Mobile": mbl,
                    "Instagram": insta,
                    "Email": email,
                    "Snapchat":snap,
                    "Twitter":twitter,
                    "LinkedIn":linkedIn,
                    "Github":github,
                    "Skype":skype,
                    "Website":web
                }
            }
            return user
        else:
            return {"error":"Please Login First"}

    def get_friends(self) -> dict:
        """

        :return:dict
        """
        if self.logged_in:
            session = session_factory(cookies=self.cookie)
            session.headers.pop('Referer')
            print("[-] Fetching Friends.")
            r = session.get("https://m.facebook.com/profile.php?v=friends")
            friends = {"friends": []}
            try:
                nextURL = re.findall('href:"/(.*?)/friends\?unit_cursor=(.*?)"', r.text)[0]
            except IndexError:
                nextURL = ""
            dots = 1
            print(f"\r[-] Creating Friends List{'.' * dots}", end="")
            if nextURL == "" or nextURL is None:
                tmp_next, tmp_list = find_friends(r)
                for i in tmp_list:
                    friends['friends'].append(i)
                print("\n[*] Successfully Created Friend List")
                nextURL = None
            else:
                dots = 2
                print(f"\r[-] Creating Friends List{'.' * dots}", end="")
                r = session.get("https://m.facebook.com/profile.php?v=friends")
                dots = 3
                while nextURL != "":
                    print(f"\r[-] Creating Friends List{'.' * dots}", end="")
                    tmp_next, tmp_list = find_friends(r)
                    for i in tmp_list:
                        friends['friends'].append(i)
                    if tmp_next != "":
                        nextURL = tmp_next
                        r = getNext(f"https://m.facebook.com/{nextURL[0]}/friends?unit_cursor={nextURL[1]}",
                                          session)
                    else:
                        print("\n[*] Successfully Created Friend List")
                        break
                    dots = dots + 1
            return friends
        else:
            return {"error":"Please Login First"}

    def get_birthdays(self) -> dict:
        if self.logged_in:
            session = session_factory(cookies=self.cookie)
            session.headers.pop('Referer')
            dots = 1
            print("[-] Fetching Birthdays.")
            # session.headers.update({"sec-ch-ua-platform":"Windows","sec-fetch-dest":"document","sec-fetch-mode":'navigate',"sec-fetch-site":"same-origin"})
            r = session.get("https://m.facebook.com/events/calendar/birthdays/")
            bds = {'birthdays': []}
            print(f"\r[-] Creating Birthdays List{'.' * dots}", end="")
            try:
                nextURL = re.findall('href:"/events/ajax/dashboard/calendar/birthdays/\?acontext=(.*?)"', r.text)[0]
            except IndexError:
                nextURL = ""
            dots = 1
            print(f"\r[-] Creating Birthdays List{'.' * dots}", end="")
            if nextURL == "" or nextURL is None:
                tmp_next, tmp_list = find_birthdays(r)
                # for i in tmp_list:
                bds['birthdays'].append(tmp_list)
                print("\n[*] Successfully Created Birthdays List")
                nextURL = None
            else:
                month = 0
                dots = 2
                s = None
                print(f"\r[-] Creating Birthdays List{'.' * dots}", end="")
                r = session.get("https://m.facebook.com/events/calendar/birthdays/")
                dots = 3
                while month <= 12:
                    print(f"\r[-] Creating Birthdays List{'.' * dots}", end="")
                    tmp_next, tmp_list = find_birthdays(r, s)
                    # for i in tmp_list:
                    bds['birthdays'].append(tmp_list)
                    if tmp_next != "":
                        nextURL = tmp_next
                        r = getNext(
                            f"https://m.facebook.com/events/ajax/dashboard/calendar/birthdays/?acontext={nextURL}",
                            session, "POST")
                        s = True
                        month = month + 1
                    else:
                        print("\n[*] Successfully Created Birthdays List")
                        break
                    dots = dots + 1
            print("\n[*] Successfully Created Birthdays Friend List")
            return bds
        else:
            return {"error":"Please Login First"}

    def get_all_chats(self, pages=1) -> dict:
        # TODO : pages
        if self.logged_in:
            chats = {
                "chats": {

                }
            }
            session = session_factory(cookies=self.cookie)
            session.headers.pop('Referer')
            r = session.get("https://m.facebook.com/messages").text.replace("<!--", "").replace("-->", "")
            soup = bs(r, "html.parser").find("div", {"class": "hidden_elem"}).find("code").find("div", {
                "id": "threadlist_rows"}).find_all("div")
            for i in soup:
                if i.get("class") is None:
                    chats['chats']['messages'] = list()
                    ru = i.find_all("div", {
                        "class": "_55wp _7om2 _5b6o _67ix _2ycx acw del_area async_del abb touchable _592p _25mv"})
                    for rui in ru:
                        kl = rui.find_all("div")
                        head = kl[3].find("header")
                        name = head.find("h3").text or None
                        msg = head.find("span").text or None
                        timestamp = str(kl[6].find("span").text) + " Ago" or None
                        msgLink = kl[8].find("a").get("href") or None
                        tmpData = {"name": name, "msg": msg, "inbox": msgLink, "timestamp": timestamp}
                        chats['chats']['messages'].append(tmpData)
                else:
                    if i.get("id") == "see_older_threads":
                        pass
            return chats
        else:
            return {"error":"Please Login First"}

    def send_message(self, user, messageText, image=None):
        if self.logged_in:
            print("[-] Initiating Message Send")
            typeof = identifier(user)
            if typeof != "id":
                print(f"[-] Finding UID of {user}")
                all_friends = self.get_friends()
                friend_tmp = find_specific_friend(typeof, user, all_friends)
            else:
                print(f"[-] Detected UID, preparing Send Message")
                friend_tmp = {
                    "uid": user
                }
            if friend_tmp is not None:
                session = session_factory(cookies=self.cookie)
                r = session.get(
                    f"https://m.facebook.com/messages/read/?tid=cid.c.{friend_tmp['uid']}:{self.user_Datagram['accountId']}")
                __a = re.findall('"encrypted":"(.*?)"', r.text)[0]
                lsd = re.findall('\["LSD",\[],\{"token":"(.*?)"},(.*?)]', r.text)[0][0]
                fb_dtsg = re.findall('MPageLoadClientMetrics.init\("(.*?)", "jazoest", "(.*?)",', r.text)[0]
                postData = {
                    "fb_dtsg": fb_dtsg[0],
                    "jazoest": fb_dtsg[1],
                    "body": messageText,
                    "waterfall_source": "message",
                    "ids[0]": friend_tmp['uid'],
                    "lsd": lsd,
                    "__a": __a,
                    "__req": "a",
                    "__user": self.user_Datagram['accountId'],
                    "photo": ""
                }
                if image is not None:
                    byteSize = os.path.getsize(image)
                    md5Hash = md5checksum(image)
                    print(f"[-] Found Image {image} , with byteSize of {byteSize} and md5Hash {md5Hash}")
                    session.headers[
                        'accept'] = "accept: image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
                    pixelData = {"step": "client_flow_begin", "qn": md5Hash,
                                 "uploader": "web_m_touch", "ref": "message"}
                    print("[-] Starting the Upload Flow", end="")
                    session.get(f"https://pixel.facebook.com/ajax/photos/logging/waterfallx.php?data=",
                                params=json.dumps(pixelData))
                    pixelData['step'] = "client_select_begin"
                    print("\r[*] Image Upload Flow Started")
                    session.get(f"https://pixel.facebook.com/ajax/photos/logging/waterfallx.php?data=",
                                params=json.dumps(pixelData))
                    session.headers['accept'] = "*/*"
                    muploadData = {
                        "allow_spherical_photo": "true",
                        "thumbnail_width": "80",
                        "thumbnail_height": "80",
                        "waterfall_id": md5Hash,
                        "waterfall_app_name": "web_m_touch",
                        "waterfall_source": "message",
                        "target_id": self.user_Datagram['accountId'],
                        "av": self.user_Datagram['accountId'],
                        "fb_dtsg": self.user_Datagram['fb_dtsg'],
                        "__user": self.user_Datagram['accountId'],
                        "lsd": lsd,
                        "__a": __a,
                        "__req": "g",
                    }
                    print("[-] Requesting Image Storage Allocation", end="")
                    session.options(f"https://upload.facebook.com/_mupload_/photo/x/saveunpublished",
                                    params=muploadData)
                    session.headers[
                        'accept'] = "accept: image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
                    pixelData = {"step": "client_select_success", "qn": md5Hash, "uploader": "web_m_touch",
                                 "ref": "message"}
                    print("\r[*] Image Storage Allocation Requested Accepted")
                    session.get(f"https://pixel.facebook.com/ajax/photos/logging/waterfallx.php?data=",
                                params=json.dumps(pixelData))
                    pixelData = {"step": "client_transfer_begin", "qn": md5Hash,
                                 "uploader": "web_m_touch", "ref": "message", "retriesNeeded": "0",
                                 "bytes": str(byteSize)}
                    print("[-] Starting the Image Upload")
                    session.get(f"https://pixel.facebook.com/ajax/photos/logging/waterfallx.php?data=",
                                params=json.dumps(pixelData))
                    mime_type = magic.from_file(image, mime=True)
                    print("[-] Creating Multipart Boundries")
                    boundary = '------WebKitFormBoundary' \
                               + ''.join(random.sample(string.ascii_letters + string.digits, 16))
                    mp_encoder = MultipartEncoder(
                        fields={
                            "photo": (str(image), open(image, 'rb'), mime_type)
                        },
                        boundary=boundary
                    )
                    session.headers['content-type'] = mp_encoder.content_type
                    session.headers['content-length'] = str(byteSize)
                    print("[-] Uploading Started", end="")
                    r = session.post(f"https://upload.facebook.com/_mupload_/photo/x/saveunpublished/",
                                     params=muploadData, data=mp_encoder)
                    jk = r.text[9:].replace('false', 'False').replace('true', "True")
                    evjk = eval(jk)
                    print("\r[*] Upload Successful")
                    del postData['photo']
                    del postData['ids[0]']
                    del postData['__req']
                    del session.headers['content-length']
                    del session.headers['content-type']

                    postData[f"photo_ids[{evjk['payload']['fbid']}]"] = evjk['payload']['fbid']
                    postData[f'ids["{friend_tmp["uid"]}"]'] = friend_tmp["uid"]
                    # postData['tids'] = f"cid.c.{self.user_Datagram['accountId']}:{friend_tmp['uid']}"
                    postData['action_time'] = str(time.time())
                    session.headers['accept'] = "*/*"
                    session.headers['x-fb-lsd'] = lsd
                print(f"[-] Sending Message to {user}")
                r = session.post("https://m.facebook.com/messages/send/?icm=1&ifcd=1", data=postData,
                                 allow_redirects=False)
                if r.text == "" or r.text is None:
                    for i in range(0, 5):
                        print(f"\r[-] Message Failed in First Try , retrying in {i}", end="")
                    r = session.post("https://m.facebook.com/messages/send/?icm=1&ifcd=1", data=postData,
                                     allow_redirects=False)
                try:
                    if r.headers['Location']:
                        return "[*] Message has been sent Successfully"
                except:
                    if "Error" not in r.text and "for" in r.text:
                        return "[*] Message has been sent Successfully"
                    else:
                        time.sleep(5)
                        r = session.post("https://m.facebook.com/messages/send/", data=postData,
                                         allow_redirects=False)
                        print(r.text)
                        try:
                            if r.headers['Location']:
                                return "[*] Message has been sent Successfully"
                        except:
                            if "Error" not in r.text and "for" in r.text:
                                return "[*] Message has been sent Successfully"
                            else:
                                return "[!] Couldn't Send the Message Please Try Again"
            else:
                return f"[!] User {user} is not Found"
        else:
            return {"error":"Please Login First"}

    def birthday_to_ics(self,filename,event_prefix=None):
        bds = self.get_birthdays()
        self.__to_ics(bds,filename,event_prefix)

