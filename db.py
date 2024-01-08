from pymongo import MongoClient

# Includes database operations
class DB:


    # db initializations
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['p2p-chat']
        self.chat_rooms_collection = self.db['chat_rooms']  # Add this line


    # checks if an account with the username exists
    def is_account_exist(self, username):
        if self.db.accounts.count_documents({'username': username}) > 0:
            return True
        else:
            return False
    
    # def is_room_exist(self, roomName):
    #     if self.db.chat_rooms.count_documents({'room_name': roomName})>0:
    #         return True
    #     else:
    #         return False

    # registers a user
    def register(self, username, password):
        account = {
            "username": username,
            "password": password
        }
        self.db.accounts.insert_one(account)


    # retrieves the password for a given username
    def get_password(self, username):
        return self.db.accounts.find_one({"username": username})["password"]

    # passcode for chat room
    def get_passcode(self, chat_room):
        return self.db.chat_rooms.find_one({"room_name": chat_room })["passcode"]

    # checks if an account with the username online
    def is_account_online(self, username):
        if self.db.online_peers.count_documents({"username": username}) > 0:
            return True
        else:
            return False
        
    # Retrive all online peers
    def retrieve_online(self):
        return self.db.online_peers.find()

    # Retrieve all Chat Rooms
    def view_rooms2(self):
        return self.db.chat_rooms.find() 
    
    # logs in the user
    def user_login(self, username, ip, port):
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        self.db.online_peers.insert_one(online_peer)
    

    # logs out the user 
    def user_logout(self, username):
        self.db.online_peers.delete_one({"username": username})
    

    # retrieves the ip address and the port number of the username
    def get_peer_ip_port(self, username):
        res = self.db.online_peers.find_one({"username": username})
        return (res["ip"], res["port"])
    
    def is_room_exist(self, room_name):
        if self.db.chat_rooms.count_documents({'room_name': room_name}) > 0:
            return True
        else:
            return False

    def create_room(self, room_id, room_name, passcode, usernameChatRoom):
        room = {
            "room_id": room_id,
            "room_name": room_name,
            "passcode": passcode,
            "members": [usernameChatRoom],  # Add the username to the members array
        }
        self.db.chat_rooms.insert_one(room)


    # def view_room_details(self, room_name):
    #     # Retrieve details of a specific chat room
    #     room = self.db.chat_rooms.find_one({"room_name": room_name})
    #     if room:
    #         members_count = len(room.get("members", []))
    #         return f"room-details {room['room_id']} {room['room_name']} {members_count} members"
    #     else:
    #         return "room-not-found"                


    #
    # Functions for joining chat room
    #
    def join_room(self, room_name, username):
        room = self.db.chat_rooms.find_one({"room_name": room_name})
        if room:
            # Add the user to the room's members list
            members = room.get("members", [])
            if username not in members:
                members.append(username)
                self.db.chat_rooms.update_one({"room_name": room_name}, {"$set": {"members": members}})
                return "join-room-success"
            else:
                return "join-room-already-member"
        else:
            return "join-room-not-found"
    def is_room_exist(self, room_name):
        return self.db.chat_rooms.count_documents({'room_name': room_name}) > 0

    # creates the room and add the username into users currently in room
    def create_room(self, room_id, room_name, passcode):
        room = {
            "room_id": room_id,
            "room_name": room_name,
            "passcode": passcode
        }
        self.chat_rooms_collection.insert_one(room)

        
    def join_room(self, room_name, passcode, username):

        room = self.db.chat_rooms.find_one({"room_name": room_name})
        if room:
            if room["passcode"] == passcode:
                # Passcode is correct, proceed to join the room
                members = room.get("members", [])
                if username not in members:
                    members.append(username)
                    self.db.chat_rooms.update_one({"room_name": room_name}, {"$set": {"members": members}})
                    return "join-room-success"
                else:
                    return "join-room-already-member"
            else:
                return "join-room-incorrect-passcode"
        else:
            return "join-room-not-found"
        
    # storing the meassg
    def store_chat_message(self, room_name, sender, message): 
        chat_message = {
            "timestamp": datetime.now(),
            "sender": sender,
            "message": message
        }
        self.db.chat_rooms.update_one(
            {"room_name": room_name},
            {"$push": {"chat_messages": chat_message}}
        )

    # Retrieve chat messages for a room
    def retrieve_chat_messages(self, room_name):
        room = self.db.chat_rooms.find_one({"room_name": room_name})
        if room:
            return room.get("chat_messages", [])
        else:
            return []

    # Retrieve members of a chat room
    def get_chat_room_members(self, room_name):
        room = self.db.chat_rooms.find_one({"room_name": room_name})
        if room:
            return room.get("members", [])
        else:
            return []


db_instance = DB()

# Retrieve all online peers
online_peers_cursor = db_instance.retrieve_online()

# Extract the usernames from the cursor and convert to a list
online_peers_list = [peer["username"] for peer in online_peers_cursor]

# Retrieve all Chat Rooms
chat_rooms_cursor = db_instance.view_rooms2()
# Extract the room names from the cursor and convert to a list
chat_rooms_list = [room["room_name"] for room in chat_rooms_cursor]

# Print the list of online peers
# print("Online peers:")
# print(str(online_peers_list))
# for peer_username in online_peers_list:
#     print(peer_username)
