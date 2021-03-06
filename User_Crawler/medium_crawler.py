# -*- coding: utf-8 -*-

import urllib2
import cookielib
import requests
import re
import json
import codecs
import os
import datetime
import random
import time
import mysql.connector
import variable
import facebook_variable


class User(object):
    def __init__(self):
        super(User, self).__init__()
        self.data = {
            'profile': {},
            'following': [],
            'followers': [],
            'latest': [],
            'recommends': [],
            'highlights': {},
            'responses': [],
        }

    def getstr(self):
        result = json.dumps(self.data, indent=4)
        return result


class Story(object):
    def __init__(self):
        super(Story, self).__init__()
        self.data = {
            'story_id': "",
            'author': "",
            'timestamp': 0,
            'published_date': "",
            'collection': {},
            'tags': [],
            'recommends': 0,
            'responses': 0,
            'response_to': "",
            'success': 1,
        }

    def getstr(self):
        result = json.dumps(self.data, indent=4)
        return result


class FBUser(object):
    def __init__(self):
        super(FBUser, self).__init__()
        self.data = {
            'user_id': '',
            'URL': '',
            'Name': '',
            'Friends': None,
            'Current City': '',
            'Hometown': '',
            'Birthday': '',
            'Gender': '',
            'Languages': '',
        }

    def getstr(self):
        result = json.dumps(self.data, indent=4)
        return result


def mark_failed_post(post):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "UPDATE posts SET failed=1 WHERE post_id='%s'" % post
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def get_story(post_id):
    url = 'https://medium.com/posts/' + post_id
    story = Story()
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    try:
        response = opener.open(req, timeout=10)
    except urllib2.URLError:
        story.data['success'] = 0
        print('----------timeout')
        mark_failed_post(post_id)
        return story
    data = response.read()

    story_id = re.findall('data-post-id="(.*?)" data-is-icon', data)
    if not story_id:
        story.data['success'] = 0
        print('----------fail to get story_id')
        mark_failed_post(post_id)
        return story
    else:
        story.data['story_id'] = story_id[0]

    author = re.findall('"username":"(.*?)","createdAt"', data)
    if not author:
        story.data['success'] = 0
        print('----------fail to get author')
        mark_failed_post(post_id)
        return story
    else:
        story.data['author'] = author[0]

    timestamp = re.findall('"firstPublishedAt":(.*?),"latestPublishedAt"', data)
    if not timestamp:
        story.data['success'] = 0
        print('----------fail to get timestamp')
        mark_failed_post(post_id)
        return story
    else:
        story.data['timestamp'] = float(timestamp[0])
        story.data['published_date'] = datetime.date.fromtimestamp(story.data['timestamp']/1000.0).isoformat()

    collection = re.findall('"approvedHomeCollection":(.*?),"newsletterId"', data)
    if not collection:
        story.data['collection'] = {}
    else:
        story.data['collection'] = json.loads(collection[0])
        story.data['collection'].pop("sections", None)
        story.data['collection'].pop("virtuals", None)
        story.data['collection'].pop("colorPalette", None)
        story.data['collection'].pop("highlightSpectrum", None)
        story.data['collection'].pop("defaultBackgroundSpectrum", None)
        story.data['collection'].pop("navItems", None)
        story.data['collection'].pop("ampLogo", None)

    tags = re.findall('false,"tags":(.*?),"socialRecommendsCount"', data)
    if not tags:
        story.data['success'] = 0
        print('----------fail to get tags')
        mark_failed_post(post_id)
        return story
    else:
        story.data['tags'] = json.loads(tags[0])

    recommends = re.findall('"recommends":(.*?),"socialRecommends"', data)
    if not recommends:
        story.data['success'] = 0
        print('----------fail to get recommends')
        mark_failed_post(post_id)
        return story
    else:
        story.data['recommends'] = eval(recommends[0])

    responses = re.findall('"responsesCreatedCount":(.*?),"links"', data)
    if not responses:
        story.data['success'] = 0
        print('----------fail to get responses')
        mark_failed_post(post_id)
        return story
    else:
        story.data['responses'] = eval(responses[0])

    response_to = re.findall('"inResponseToPostId":"(.*?)","inResponseToPost"', data)
    if not response_to:
        story.data['response_to'] = ''
    else:
        story.data['response_to'] = response_to[0]

    return story


def get_following(user_id):
    url = 'https://medium.com/_/api/users/' + user_id + '/following'
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    following = re.findall('"username":"(.*?)","createdAt"', data)
    following_set = set(following)
    to = re.findall('"to":"(.*?)"}}},"v"', data)
    while to:
        url = 'https://medium.com/_/api/users/' + user_id + '/following?to=' + to[0]
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)
        req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/50.0.2661.102 Safari/537.36')
        response = opener.open(req, timeout=10)
        data = response.read()
        following = re.findall('"username":"(.*?)","createdAt"', data)
        following_set.update(following)
        to = re.findall('"to":"(.*?)"}}},"v"', data)
    return list(following_set)


def get_followers(user_id):
    url = 'https://medium.com/_/api/users/' + user_id + '/followers'
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    followers = re.findall('"username":"(.*?)","createdAt"', data)
    followers_set = set(followers)
    to = re.findall('"to":"(.*?)"}}},"v"', data)
    while to:
        url = 'https://medium.com/_/api/users/' + user_id + '/followers?to=' + to[0]
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)
        req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/50.0.2661.102 Safari/537.36')
        response = opener.open(req, timeout=10)
        data = response.read()
        followers = re.findall('"username":"(.*?)","createdAt"', data)
        followers_set.update(followers)
        to = re.findall('"to":"(.*?)"}}},"v"', data)
    return list(followers_set)


def get_latest(user_id):
    url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=latest'
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    latest = re.findall('"postId":"(.*?)"},"randomId"', data)
    latest_set = set(latest)
    to = re.findall('"to":"(.*?)","source":"latest"', data)
    while to:
        url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=latest&to=' + to[0]
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)
        req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/50.0.2661.102 Safari/537.36')
        response = opener.open(req, timeout=10)
        data = response.read()
        latest = re.findall('"postId":"(.*?)"},"randomId"', data)
        latest_set.update(latest)
        to = re.findall('"to":"(.*?)","source":"latest"', data)
    return list(latest_set)


def get_recommends(user_id):
    url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=has-recommended'
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    recommends = re.findall('w":{"postId":"(.*?)"},"randomId"', data)
    recommends_set = set(recommends)
    to = re.findall('"to":"(.*?)","source":"has-recommended"', data)
    while to:
        url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=has-recommended&to=' + to[0]
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)
        req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/50.0.2661.102 Safari/537.36')
        response = opener.open(req, timeout=10)
        data = response.read()
        recommends = re.findall('w":{"postId":"(.*?)"},"randomId"', data)
        recommends_set.update(recommends)
        to = re.findall('"to":"(.*?)","source":"has-recommended"', data)
    return list(recommends_set)


def get_highlights(user_id):
    url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=quotes'
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    highlights = re.findall('","postId":"(.*?)","userId":"', data)
    highlights_set = set(highlights)
    to = re.findall('"to":"(.*?)","source":"quotes"', data)
    while to:
        url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=quotes&to=' + to[0]
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)
        req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/50.0.2661.102 Safari/537.36')
        response = opener.open(req, timeout=10)
        data = response.read()
        highlights = re.findall('","postId":"(.*?)","userId":"', data)
        highlights_set.update(highlights)
        to = re.findall('"to":"(.*?)","source":"quotes"', data)
    return list(highlights_set)


def get_responses(user_id):
    url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=responses'
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    responses = re.findall('w":{"postId":"(.*?)"},"randomId"', data)
    responses_set = set(responses)
    to = re.findall('"to":"(.*?)","source":"responses"', data)
    while to:
        url = 'https://medium.com/_/api/users/' + user_id + '/profile/stream?source=responses&to=' + to[0]
        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url)
        req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                        Chrome/50.0.2661.102 Safari/537.36')
        response = opener.open(req, timeout=10)
        data = response.read()
        responses = re.findall('w":{"postId":"(.*?)"},"randomId"', data)
        responses_set.update(responses)
        to = re.findall('"to":"(.*?)","source":"responses"', data)
    return list(responses_set)


def mark_visited(username):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "UPDATE users SET visited=1 WHERE username='%s'" % username
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def mark_failed(username):
    print('-----mark failed')
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "UPDATE users SET failed=1 WHERE username='%s'" % username
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def post_exist(post):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    try:
        sql = "INSERT INTO posts VALUE('%s', %s, %s)" % (post, 1, 0)
        cur.execute(sql)
        cur.close()
        conn.commit()
        conn.close()
        return False
    except:
        cur.close()
        conn.close()
        return True


def get_posts(user):
    post_list = user.data['latest'] + user.data['recommends'] + user.data['highlights'] + user.data['responses']
    post_list = list(set(post_list))
    for post in post_list:
        if not post_exist(post):
            out = codecs.open("./Posts/%s.json" % post, 'w', 'utf-8')
            out.write(get_story(post).getstr())
            out.close()
    for post in user.data['responses']:
        post = get_story(post).data['response_to']
        if post and (not post_exist(post)):
            out = codecs.open("./Posts/%s.json" % post, 'w', 'utf-8')
            out.write(get_story(post).getstr())
            out.close()


def get_twitter_profile(username, twitter_id):
    url = "https://twitter.com/" + str(twitter_id) + "?lang=en"
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    response = opener.open(req, timeout=10)
    data = response.read()
    profile_data = re.findall('class="json-data" value="(.*?)">', data)
    profile = json.loads(profile_data[0].replace('&quot;', '"'))
    profile.pop("promptbirdData", None)
    profile.pop("wtfOptions", None)
    profile.pop("typeaheadData", None)
    profile.pop("dm", None)
    profile.pop("initialState", None)
    profile.pop("activeHashflags", None)
    profile.pop("keyboardShortcuts", None)
    profile.pop("deciders", None)
    out = codecs.open("./Twitter/%s_t.json" % username, 'w', 'utf-8')
    out.write(json.dumps(profile, indent=4))
    out.close()


def mark_visited_twitter(username, twitter_id):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "INSERT INTO twitter VALUE('%s', '%s', %s, %s)" % (username, twitter_id, 1, 0)
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def mark_failed_twitter(username, twitter_id):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "UPDATE twitter SET failed=1 WHERE username='%s' and twitter_id='%s'" % (username, twitter_id)
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def get_facebook_profile(username, user_id):
    print(user_id)
    user = FBUser()

    user.data['user_id'] = user_id

    login_url = 'https://m.facebook.com/login'
    s = requests.session()
    login_data = {
        'email': facebook_variable.username,
        'pass': facebook_variable.password
    }
    s.post(login_url, login_data)

    time.sleep(1)
    url = 'https://facebook.com/' + user_id
    response = s.get(url)
    data = response.content

    URL = re.findall('URL=/(.*?)\?_fb_noscript=1', data)
    if URL:
        user.data['URL'] = URL[0]
    else:
        user.data['URL'] = user_id
    print(user.data['URL'])

    time.sleep(1)
    url = 'https://m.facebook.com/' + user.data['URL']
    response = s.get(url)
    data = response.content

    name = re.findall('<title>(.*?)</title>', data)
    if name:
        user.data['Name'] = name[0]
    else:
        print('-----no Name to show')

    if user.data['Name'] == 'Page Not Found':
        print('-----blocked')
        mark_failed_facebook(username, user_id)
        return

    friends = re.findall('See All Friends \((.*?)\)</a>', data)
    if friends:
        user.data['Friends'] = int(friends[0])
    else:
        print('-----no Friends to show')

    current_city = re.findall('Current City<(.*?)a>', data)
    if current_city:
        current_city = re.findall('<a href="/(.*?)/', current_city[0])
        if current_city:
            current_city = re.findall('>(.*?)<', current_city[0])
    if current_city:
        user.data['Current City'] = current_city[0]
    else:
        print('-----no Current City to show')

    hometown = re.findall('Hometown<(.*?)a>', data)
    if hometown:
        hometown = re.findall('<a href="/(.*?)/', hometown[0])
        if hometown:
            hometown = re.findall('>(.*?)<', hometown[0])
    if hometown:
        user.data['Hometown'] = hometown[0]
    else:
        print('-----no Hometown to show')

    birthday = re.findall('Birthday</span></div></td><td(.*?)div>', data)
    if birthday:
        birthday = re.findall('><(.*?)/', birthday[0])
        if birthday:
            birthday = re.findall('>(.*?)<', birthday[0])
    if birthday:
        user.data['Birthday'] = birthday[0]
    else:
        birthday = re.findall('Birth Year</span></div></td><td(.*?)div>', data)
        if birthday:
            birthday = re.findall('><(.*?)/', birthday[0])
            if birthday:
                birthday = re.findall('>(.*?)<', birthday[0])
        if birthday:
            user.data['Birthday'] = birthday[0]
        else:
            print('-----no Birthday to show')

    gender = re.findall('Gender</span></div></td><td(.*?)div>', data)
    if gender:
        gender = re.findall('><(.*?)/', gender[0])
        if gender:
            gender = re.findall('>(.*?)<', gender[0])
    if gender:
        user.data['Gender'] = gender[0]
    else:
        print('-----no Gender to show')

    languages = re.findall('Languages</span></div></td><td(.*?)div>', data)
    if languages:
        languages = re.findall('><(.*?)/', languages[0])
        if languages:
            languages = re.findall('>(.*?)<', languages[0])
    if languages:
        user.data['Languages'] = languages[0]
    else:
        print('-----no Languages to show')

    out = codecs.open("./Facebook/%s_fb.json" % username, 'w', 'utf-8')
    out.write(user.getstr())
    out.close()


def mark_visited_facebook(username, facebook_id):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "INSERT INTO facebook VALUE('%s', '%s', %s, %s)" % (username, facebook_id, 1, 0)
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def mark_failed_facebook(username, facebook_id):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "UPDATE facebook SET failed=1 WHERE username='%s' and facebook_id='%s'" % (username, facebook_id)
    cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()


def get_user(username):
    if not os.path.exists('./Users'):
        os.mkdir('./Users')
    if not os.path.exists('./Posts'):
        os.mkdir('./Posts')
    if not os.path.exists('./Twitter'):
        os.mkdir('./Twitter')
    if not os.path.exists('./Facebook'):
        os.mkdir('./Facebook')

    print(username)

    user = User()

    url = 'https://medium.com/@' + username
    cj = cookielib.MozillaCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(url)
    req.add_header("User-agent", 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
                    Chrome/50.0.2661.102 Safari/537.36')
    try:
        response = opener.open(req, timeout=10)
    except:
        print('-----fail to get data')
        mark_failed(username)
        return
    data = response.read()

    profile = re.findall('"userMeta":(.*?)"UserMeta"}', data)
    if not profile:
        print('-----fail to get profile')
        mark_failed(username)
        return
    else:
        user.data['profile'] = json.loads(profile[0]+'"UserMeta"}')
        print('-----profile')

    user_id = user.data['profile']['user']['userId']

    try:
        user.data['following'] = get_following(user_id)
        print('-----following')
    except:
        print('-----fail to get following')
        mark_failed(username)
        return

    try:
        user.data['followers'] = get_followers(user_id)
        print('-----followers')
    except:
        print('-----fail to get followers')
        mark_failed(username)
        return

    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password,
                                   database='Medium', charset='utf8')
    cur = conn.cursor()
    for following in user.data['following']:
        try:
            sql = "INSERT INTO users VALUE('%s', %s, %s, '%s')" % (following, 0, 0, variable.ip)
            cur.execute(sql)
            conn.commit()
            variable.queue.append(following)
        except:
            continue
    for follower in user.data['followers']:
        try:
            sql = "INSERT INTO users VALUE('%s', %s, %s, '%s')" % (follower, 0, 0, variable.ip)
            cur.execute(sql)
            conn.commit()
            variable.queue.append(follower)
        except:
            continue
    cur.close()
    conn.close()

    try:
        user.data['latest'] = get_latest(user_id)
        print('-----latest')
    except:
        print('-----fail to get latest')
        mark_failed(username)
        return

    try:
        user.data['recommends'] = get_recommends(user_id)
        print('-----recommends')
    except:
        print('-----fail to get recommends')
        mark_failed(username)
        return

    try:
        user.data['highlights'] = get_highlights(user_id)
        print('-----highlights')
    except:
        print('-----fail to get highlights')
        mark_failed(username)
        return

    try:
        user.data['responses'] = get_responses(user_id)
        print('-----responses')
    except:
        print('-----fail to get responses')
        mark_failed(username)
        return

    out = codecs.open("./Users/%s.json" % username, 'w', 'utf-8')
    out.write(user.getstr())
    out.close()

    try:
        get_posts(user)
        print('-----posts')
    except:
        print('-----fail to get posts')

    twitter_id = user.data['profile']['user']['twitterScreenName']
    print('-----twitter: ' + twitter_id)
    if twitter_id:
        try:
            mark_visited_twitter(username, twitter_id)
            get_twitter_profile(username, twitter_id)
            print('-----twitter')
        except:
            mark_failed_twitter(username, twitter_id)
            print('-----fail to get Twitter')

    facebook_id = user.data['profile']['user']['facebookAccountId']
    print('-----facebook: ' + facebook_id)
    if facebook_id:
        try:
            mark_visited_facebook(username, facebook_id)
            get_facebook_profile(username, facebook_id)
            print('-----facebook')
        except:
            mark_failed_facebook(username, facebook_id)
            print('-----fail to get Facebook')

    print("-----%s obtained" % username)


def get_queue(ip):
    conn = mysql.connector.connect(host=variable.host, port=3306, user=variable.username, password=variable.password, database='Medium', charset='utf8')
    cur = conn.cursor()
    sql = "SELECT username FROM users WHERE visited=0 and failed=0 and ip='%s'" % ip
    cur.execute(sql)
    result = cur.fetchall()
    cur.close()
    conn.commit()
    conn.close()
    queue = []
    for user in result:
        queue.append(user[0])
    for i in range(5):
        random.shuffle(queue)
    return queue


def bfs():
    while variable.queue:
        username = variable.queue.pop(0)
        mark_visited(username)
        try:
            get_user(username)
        except:
            print('fail to get user')


if __name__ == '__main__':
    variable.queue = get_queue(variable.ip)
    bfs()
