#!/usr/bin/env python

import shelve
from subprocess import check_output
import flask
from flask import request, url_for,redirect,jsonify
from flask import make_response
from os import environ
from flask import abort
import random
import string
import MySQLdb
import json
import requests
import datetime
import csv

#URL to fetch json of geolocation data
geo_ip_url = 'http://www.telize.com/geoip/'


app = flask.Flask(__name__)
app.debug = True

dbb = shelve.open("shorten.db")

def write_log(type_log,request,val):
    username = request.cookies.get('username','')
    if username == '':
        username = 'anonymous'
    val = type_log + [username]+ val  +  ["1"] + [get_ip(request)]  + [datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")] + [request.headers["User-Agent"]]
    with open('log.csv', 'a') as f:
        writer = csv.writer(f,delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(val)
        f.close()
###
# POST, GET method, stores url and shorten_url then returns result
###
@app.route('/shorts', methods=['POST','GET'])
def shorts():
    # POST method
    if request.method == 'POST':
        username = request.cookies.get('username','')
        return create_short(username)
    # GET method
    return flask.render_template('shorts.html',
                                         error= "Error: type your short url. i.e. shorts/name")




def create_short(username):
    # retrieve url out the form
    long_url= request.form.get("long_url").encode('utf-8')
    # add http:// prefix if it's not there
    if long_url[:7] != 'http://' and long_url[:8] != 'https://':
        long_url = "http://" + long_url
    # retrieve shorten string
    short_str = request.form.get("short_str").encode('utf-8')
    # automaticlly generate short string when it's not sent by form
    # Extra credit
    db = MySQLdb.connect(host="localhost", user="ashwin_chandak", passwd="ivB2hnBX",db="ashwin_chandak") # database info
    db.autocommit(True)
    cur = db.cursor()
    cur.execute("SELECT * FROM links WHERE short = '%s'" % short_str)
    #short_url_db = db.get(short_str,'')
    short_url_db = int(cur.rowcount)
    if short_str == '' or short_url_db > 0:
        short_str = get_random_string()
    # store to database
    if username == '':
        username = 'anonymous'
    cur.execute("SELECT * FROM links WHERE url = '%s'" % long_url)
    results = cur.fetchone()
    if cur.rowcount < 1 :
        cur.execute("""INSERT INTO links (short,url,created_by) VALUES ('%s','%s','%s')""" % (short_str,long_url, username,))
    else:
        short_str = results[1]
    server_url="/shorts"
    # return html to /server/shorts
    return flask.render_template(
                                 'shorts.html',
                                 url= request.referrer.replace("/home",server_url) + "/" +  short_str)


###
# Generate 7 chars long string
###
def get_random_string(length=10):
    SIMPLE_CHARS = string.ascii_letters
    return ''.join(random.choice(SIMPLE_CHARS) for i in xrange(length))

##
# Get client ip address
#
def get_ip(request):
    if len(request.access_route) > 1:
        return request.access_route[-1]
    else:
        return request.access_route[0]

####Use url of geolocation service with client ip address to get a json of
#geolocation data for that address
###

def get_geolocation(ip):
    url = '{}/{}'.format(geo_ip_url, ip)
    response = requests.get(url)
    response.raise_for_status()
    return response.json

###
# For project purpose:
# GET method, redirect to url
###
@app.route('/shorts/<short>', methods=['GET'])
def redirect_short(short):
    val =  ["shorts.html/" + short]  
    write_log(["V"],request,val)
    if short[len(short)-1] == '_':
        db = MySQLdb.connect(host="localhost", user="ashwin_chandak", passwd="ivB2hnBX",db="ashwin_chandak") # database info
        cur = db.cursor()
        cur.execute("SELECT * FROM clicks WHERE short_id = '%s'" % short[0:len(short)-1])
        short_stats = cur.fetchall()
        return flask.render_template('stats.html',short_url = short[0:len(short)-1], number_clicks = len(short_stats),stats = short_stats)

    # retrieve short string from url
    db = MySQLdb.connect(host="localhost", user="ashwin_chandak", passwd="ivB2hnBX",db="ashwin_chandak") # database info
    db.autocommit(True)
    cur = db.cursor()
    cur.execute("SELECT * FROM links WHERE short = '%s'" % short)

    # redirect if it's exist
    if cur.rowcount > 0:
        results = cur.fetchone()
        long_url= results[2]
        app.logger.debug("redirect to " + long_url)

	#Get IP address and json of geolocationdata, so that latitude and longitude entries can be stored in db
        ip_address = get_ip(request)
        geodata = get_geolocation(ip_address)
        app.logger.debug(geodata['latitude'] + "," +  geodata['longitude'])
        cur.execute("INSERT INTO clicks (`short_id`,`ip_address`,`lat`,`long`) VALUES ('%s','%s',%s,%s)" % ( short,ip_address,geodata['latitude'],geodata['longitude']))
	return redirect(long_url)    
# return 404 if not found
    abort(404)




###
#  GET method, retreive user links
###
@app.route('/links', methods=['GET'])
def links():
    val =  ["links.html"]  
    write_log(["V"],request,val)
    db = MySQLdb.connect(host="localhost", user="ashwin_chandak", passwd="ivB2hnBX",db="ashwin_chandak") # database info
    db.autocommit(True)
    cur = db.cursor()
    username = request.cookies.get('username')
    
    if username == "" :
        abort(404)
    cur.execute("SELECT * FROM links WHERE created_by = '%s'" % username)
    links = cur.fetchall()
    return flask.render_template('links.html',user_links = links)


##
# Retreive user info
###
def get_user_info(cur,username):
        query_data = (username)
        try:
            # insert user data into db
            cur.execute("SELECT * FROM users WHERE username = '%s'" % query_data)
            results = cur.fetchone()
            firstname_r = results[3]
            lastname_r = results[4]
            email_r = results[2]
            cur.close()
            return [firstname_r, lastname_r, email_r]
        except:
            return []

###
# GET, POST to Update user profile
###
@app.route('/profile', methods=['POST','GET'])
def profile():
    val =  ["profile.html"]  
    write_log(["V"],request,val)
    db = MySQLdb.connect(host="localhost", user="ashwin_chandak", passwd="ivB2hnBX",db="ashwin_chandak") # database info
    db.autocommit(True)
   
    cur = db.cursor()
    username = request.cookies.get('username')
    
    if request.method == 'GET':
        if username == "" :
            return flask.render_template('home.html')
        user_data = get_user_info(cur, username)
        if len(user_data) > 0:
            return flask.render_template('profile.html',firstname = """%s"""% user_data[0],lastname = user_data[1],email = user_data[2])
        else:
            abort(404)

    else:
        firstname = request.form.get("firstname").encode('utf-8')
        lastname = request.form.get("lastname").encode('utf-8')
        password = request.form.get("password").encode('utf-8')
        newpassword = request.form.get("newpassword","").encode('utf-8')
        email = request.form.get("email").encode('utf-8')
        try:
            if newpassword == "":
                update_data = (firstname,lastname,email,username,password,)
                cur.execute("""UPDATE users set firstname = '%s' , lastname = '%s' , email = '%s' WHERE username = '%s' AND password = '%s'""" % update_data)
            else:
                update_data = (firstname,lastname,email,newpassword,username,password,)
                #app.logger.debug("""UPDATE users set firstname = '%s' , lastname = '%s' , email = '%s', password='%s' WHERE username = '%s' AND password = '%s'""" % update_data)
                cur.execute("""UPDATE users set firstname = '%s' , lastname = '%s' , email = '%s', password='%s' WHERE username = '%s' AND password = '%s'""" % update_data)
            #return str(cur.rowcount ) + " " + newpassword
            if int(cur.rowcount) < 1:
                user_data = get_user_info(cur, username)
                cur.close()
                db.close()
                return flask.render_template('profile.html',update_fail= "fail" ,firstname = """%s"""% user_data[0],lastname = user_data[1],email = user_data[2])
            else:
                user_data = get_user_info(cur, username)
                name = user_data[0] + " " + user_data[1]
                resp = make_response(flask.render_template('profile.html',update_success= "Success",firstname = """%s"""% user_data[0],lastname = user_data[1],email = user_data[2]))
                resp.set_cookie('username', username,10*24*60*60)
                resp.set_cookie('name', name,10*24*60*60)
                cur.close()
                db.close()
                return resp
        except:
            user_data = get_user_info(cur, username)
            cur.close()
            db.close()
            return flask.render_template('profile.html')






###
# Home Resource:
# Only supports the GET method, returns a homepage represented as HTML
###
@app.route('/home', methods=['GET'])
def home():
    val =  ["home.html"]  
    write_log(["V"],request,val)
    return flask.render_template('home.html')


@app.route('/home', methods=['POST'])
def home_post():
    db = MySQLdb.connect(host="localhost", port=3306, user="ashwin_chandak", passwd="ivB2hnBX",db="ashwin_chandak") # database info
    cur = db.cursor()
    sign_in_up = request.form.get("sign").encode('utf-8')
    val =  ["home.html"] 
    if sign_in_up == 'signup': # sign up request
        # collect user data
        firstname = request.form.get("firstname").encode('utf-8')
        lastname = request.form.get("lastname").encode('utf-8')
        username = request.form.get("username").encode('utf-8')
        password = request.form.get("password").encode('utf-8')
        email = request.form.get("email").encode('utf-8')
        insert_data = (firstname,lastname,username,password,email)
        try:
            # insert user data into db
            cur.execute("INSERT INTO users (firstname,lastname,username,password,email) VALUES (%s,%s,%s,%s,%s)",insert_data)
            db.commit()
            cur.close()
            db.close()
            write_log(["U"],request,val)
            return flask.render_template('home.html',signup_success="Success")
        except:
            db.rollback()
            cur.close()
            db.close()
            write_log(["Ux"],request,val)
            return "Error: unable to fecth data!"
    elif sign_in_up == 'signin': # sign in request
        # collect user data
        username = request.form.get("username","").encode('utf-8')
        password = request.form.get("password","").encode('utf-8')
        if username == "" or password == "":
            return
        query_data = (username,password)
        try: # query user
            cur.execute("SELECT * FROM users WHERE username = %s AND password = %s",query_data)
            results = cur.fetchone()
            if cur.rowcount == 1:
                name = results[3] + " " + results[4]
                resp = make_response(flask.render_template('home.html'))
                resp.set_cookie('username', username,10*24*60*60)
                resp.set_cookie('name', name,10*24*60*60)
                cur.close()
                db.close()
                write_log(["S"],request,val)
                return resp
            else:
                cur.close()
                db.close()
                return flask.render_template('home.html',signin_fail="Fail")
        except:
            write_log(["Sx"],request,val)
            return "Error: unable to fecth data!"



###
# Wiki Resource:
# GET method will redirect to the resource stored by PUT, by default: Wikipedia.org
# POST/PUT method will update the redirect destination
###
@app.route('/wiki', methods=['GET'])
def wiki_get():
    """Redirects to wikipedia."""
    destination = dbb.get('wiki', 'http://en.wikipedia.org')
    app.logger.debug("Redirecting to " + destination)
    return flask.redirect(destination)

@app.route("/wiki", methods=['PUT', 'POST'])
def wiki_put():
    """Set or update the URL to which this resource redirects to. Uses the
    `url` key to set the redirect destination."""
    wikipedia = request.form.get('url', 'http://en.wikipedia.org')
    dbb['wiki'] = wikipedia
    return "Stored wiki => " + wikipedia


###
# i253 Resource:
# Information on the i253 class. Can be parameterized with `relationship`,
# `name`, and `adjective` information
#
# TODO: The representation for this resource is broken. Fix it!
# Set the correct MIME type to be able to view the image in your browser
##/
@app.route('/i253')
def i253():
    """Returns a PNG image of madlibs text"""
    relationship = request.args.get("relationship", "friend")
    name = request.args.get("name", "Jim")
    adjective = request.args.get("adjective", "fun")

    resp = flask.make_response(
            check_output(['convert', '-size', '600x400', 'xc:transparent',
                '-frame', '10x30',
                '-font', '/usr/share/fonts/liberation/LiberationSerif-BoldItalic.ttf',
                '-fill', 'black',
                '-pointsize', '32',
                '-draw',
                  "text 30,60 'My %s %s said i253 was %s'" % (relationship, name, adjective),
                '-raise', '30',
                'png:-']), 200);
    # Comment in to set header below
    resp.headers['Content-Type'] = request.header['accept']

    return resp


if __name__ == "__main__":
    app.run(port=int(environ['FLASK_PORT']))
