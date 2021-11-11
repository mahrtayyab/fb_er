# fb_er
## A Strong Facebook Scraper and Client
> ### You can use cookies as well as your username and password to login
> ## Login with password is broken , working on fix
> ### ~~2-Factor Authentication is also supported~~ (working on fix) 

> ### Example:
> Facebook("username/email/phone_number","password") <br/>
> Facebook(use_cookies=True,cookie="cookie_Value")
# Prerequisites
* Internet Connection
* Python 3.6+
* BeautifulSoup (Python Module)
* Requests (Python Module)
* magic (Python Module)
* requests_toolbelt (Python Module)
* cssutils (Python Module)
* ics (Python Module)
> requirements.txt is also available


# All Functions
* userinfo()
* get_friends()
* get_birthdays()
* get_all_chats()
* send_message()
* birthday_to_ics()

# Get User Info
## Description:
This method can be used to get info of a user
## Optional Parameters
* user : str -> user id of a user if you are trying to get user info of users other than you
##  Output:
* Type -> dict
* Structure
```json
{
     "AccountId": "1000000000000",
     "bio": "Using fb_er.",
     "contact_details": {
           "Email": "",
           "Github": "",
           "Instagram": "",
           "LinkedIn": "",
           "Mobile": "",
           "Skype": "",
           "Snapchat": "",
           "Twitter": "",
           "Website": ""
     },
     "dateOfBirth": "dd mm yyyy",
     "gender": "",
     "joinedOn": "",
     "livesIn": "",
     "name": {
       "alternative_name": "",
       "name": ""
     },
     "total_friends": "161"
}
```
## Example:

```python
from fb_er.client import Facebook

cookies = "cookies_value"
user = Facebook(use_cookies=True, cookie=cookies)
print(user.userinfo())
```


# Get Friends
## Description:
This method can be used to get all the friends in a dict
##  Output:
* Type -> dict
* Structure
```json
{
  "friends": [
    {
      "facebook_profile_url": "https://facebook.com//profile",
      "fb_username": "/username_of_friend",
      "name": "name_of_friend",
      "uid": "user_id of friend"
    },
    {}
  ]
}
```
## Example:

```python
from fb_er.client import Facebook

user = Facebook(username="username/email/phone_number", password="password")
print(user.get_friends())
```

# Get Birthdays
## Description:
This method can be used to get birthdays on friends in next 12 months
##  Output:
* Type -> dict
* Structure
```json
{
  "birthdays": [
    {
      "Later in Current Month": [
        {
          "birthday": "date_of_birth",
          "name": "friend's name"
        }
      ],
      "Recent Birthdays": [
        {}
      ],
      "Upcoming Birthdays": [
        {}
      ]
    },
    {
      "November": [
        {}
      ]
    },
    {
      "December": [
        {}
      ]
    }
    
  ]
}
```
## Example:

```python
from fb_er.client import Facebook

user = Facebook(username="username/email/phone_number", password="password")
print(user.get_birthdays())
```
# Get Chats
## Description:
This method can be used to get last 6 chats in a dict
##  Output:
* Type -> dict
* Structure
```json
{
  "chats": {
    "messages": [
      {
        "inbox": "url_to_direct_inbox_of_that_friend",
        "msg": "last_message_from_that_friend",
        "name": "name_of_sender",
        "timestamp": "last_message_sent_timestamp"
      },
      {}
    ]
  }
}
```
## Example:

```python
from fb_er.client import Facebook

cookies = "cookies_value"
user = Facebook(use_cookies=True, cookie=cookies)
print(user.get_all_chats())
```

# Sending Message
## Description:
This method can be used to send message to a user
## Required Parameters
* user : str -> user_id , name or username of the recipient
* messageText : str -> body of the message to be sent

## Optional Parameter
* image : str[path] -> path of an image as a string which can be sent 
## Example:

```python
from fb_er.client import Facebook

cookies = "cookies_value"
user = Facebook(use_cookies=True, cookie=cookies)
user.send_message("Facebook_user", "Hi Sending message using fb_er")
```

# Birthday to ICS
## Description:
ICS is a CALENDER file which is supported by all major Calender , you can now get all the birthdays from of next year and import it to an ICS file , which then can be import to your favourite Calender App.
## Required Parameters
* filename : str [path] -> Path of file , where you want to create the ics file
## Optional Parameter
* event_prefix : str -> Prefix Title of Event , the script will automatically add the name of user at the end
## Example:

```python
from fb_er.client import Facebook

cookies = "cookies_value"
user = Facebook(use_cookies=True, cookie=cookies)
user.birthday_to_ics()
```
# Updates:
## Update 0.1:
* Fixed all known bugs except login
* Added [birthday_to_ics](#birthday-to-ics) function , which can be used to import Facebook Birthdays to ICS