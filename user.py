from app import app
from pymongo import MongoClient
from src.config import DBURL
from bson.json_util import dumps
from bson import ObjectId
from flask import request, jsonify
import re
import json
from src.helpers.errorHelpers import errorHelper, APIError, Error404, checkValidParams
from src.helpers.apiResponse import data

client = MongoClient(DBURL)
print(f"connected to db {DBURL}")

db = client.get_default_database()["users"]

@app.route('/')
def hello():
    return '<h1>Hello!</h1>'

@app.route('/user/create/<username>')
@errorHelper()
def create_user(username):
    """
    Function that allows creation of a new username but will warn us if name is already selected
    """
    res = db.find_one({'username': username},{'_id':0})
    if res:
        raise APIError('Username already exists. Select a new option')
    else:
        dic={
            'user_name':username,
            'chats': []
        }
    user_id=db.insert_one(dic)
    return json.dumps({'user_id':str(user_id.inserted_id)})

db_chats = client.get_default_database()['chats']
  
@app.route("/chats/create") #?ids=<arr>&name=<chatname>
@errorHelper()
def insertChat():
    """
  Function that allows creation of a new chats groups
    """ 
    arr = request.args.get("ids")
    name= request.args.get("name",default='')
    
    #creation of a new chats with the users included in arr
    if arr:
        dic={   
            'chat_name': name,
            'users_list':[],
            'messages_list':[]
        }
        chat_id=db_chats.insert_one(dic)
        #insert the users in the chats
        chatId=chat_id.inserted_id
        for user_id in arr:
            addChatUser(chatId, user_id)
        #update of the users chats_list by adding the chats id
        for user_id in arr:
            post=db.find_one({'_id':ObjectId(user_id)})
            post['chats_list'].append(ObjectId(chat_id.inserted_id))
            db.update_one({'_id':ObjectId(user_id)}, {"$set": post}, upsert=False)

    else:
        print("ERROR")
        raise APIError("Tienes que mandar un query parameter ?ids=<arr>&name=<chatname>")
    
    return json.dumps({'chat_id':str(chat_id.inserted_id)})


"""
  Function that adds a user to a chats, this is optional just in case you want to add more users to a chats after it's creation.
"""

@app.route("/chats/<chat_id>/adduser") #?user_id=<user_id>
@errorHelper()
def addChatUser(chat_id, user_id=None):
    if user_id==None:
        user_id= request.args.get("user_id")
    if user_id!=None and chat_id!=None:
        #update of the chats document by adding the user id
        post=db_chats.find_one({'_id':ObjectId(chat_id)})
        if ObjectId(user_id) not in post['users_list']:
            post['users_list'].append(ObjectId(user_id))
        db_chats.update_one({'_id':ObjectId(chat_id)}, {"$set": post}, upsert=False)
        
        #update of the user permissions by adding the chats id
        post=db.find_one({'_id':ObjectId(user_id)})
        if ObjectId(chat_id) not in post['chats_list']:
            post['chats_list'].append(ObjectId(chat_id))
        db.update_one({'_id':ObjectId(user_id)}, {"$set": post}, upsert=False)
    elif not chat_id:
        print("ERROR")
        raise Error404("chat_id not found")
    elif not user_id:
        print("ERROR")
        raise APIError("You should send these query parameters ?user_id=<user_id>")

    return json.dumps({'chat_id': str(chat_id)})


db_messages = client.get_default_database()['messages']


@app.route("/chats/<chat_id>/addmessage") #?user_id=<user_id>&text=<text>
@errorHelper()
def addMessage(chat_id):
    """
  Function that adds a message to the conversation. 
  Help: Before adding the chats message to the database, 
  check that the incoming user is part of this chats id. If not, raise an exception.
    """ 
    user_id= request.args.get("user_id")
    text= request.args.get("text")
    
    #check if the user has the permission to post in the chats or raise an exception
    get=db_chats.find_one({"_id":ObjectId(chat_id) })
    if not ObjectId(user_id) in get['users_list']:
        raise PermissionError("Permission denied")

    #add the message to the messages collection and get the id
    
    dic={
         'user_id': ObjectId(user_id),
         'text':text,
         'chat_id':ObjectId(chat_id)
    }
    message_id=db_messages.insert_one(dic)
    
    #add the message text to the messages_list of the chats

    post=db_chats.find_one({"_id":ObjectId(chat_id)})
    post['messages_list'].append(message_id.inserted_id)
    db_chats.update_one({'_id':ObjectId(chat_id)}, {"$set": post}, upsert=False)
    
    return json.dumps({'message_id':str(message_id.inserted_id)})


"""
Function that gets all messages from `chat_id`
"""

@app.route("/chats/<chat_id>/list") 
@errorHelper()
def getMessages(chat_id):
    get=db_chats.find_one({"_id":ObjectId(chat_id)})
    messages_ids=[]
    for el in get['messages_list']:
        messages_ids.append(str(el))
    diz={}
    for m in messages_ids:
        r=db_messages.find_one({'_id':ObjectId(m)})
        diz[m]=r['text']
    return json.dumps(diz)