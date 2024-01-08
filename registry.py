
'''
    ##  Implementation of registry
    ##  150114822 - Eren Ulaş
'''

from socket import *
import threading
import select
import logging
import db
from random import randint

# This class is used to process the peer messages sent to registry
# for each peer connected to registry, a new client thread is created
class ClientThread(threading.Thread):
    # initializations for client thread
    def __init__(self, ip, port, tcpClientSocket):
        threading.Thread.__init__(self)
        # ip of the connected peer
        self.ip = ip
        # port number of the connected peer
        self.port = port
        # socket of the peer
        self.tcpClientSocket = tcpClientSocket
        # username, online status and udp server initializations
        self.username = None
        self.isOnline = True
        self.udpServer = None
        print("New thread started for " + ip + ":" + str(port))

    # main of the thread
    def run(self):
        # locks for thread which will be used for thread synchronization
        self.lock = threading.Lock()
        print("Connection from: " + self.ip + ":" + str(port))
        print("IP Connected: " + self.ip)
        
        while True:
            try:
                # waits for incoming messages from peers
                message = self.tcpClientSocket.recv(1024).decode().split()
                logging.info("Received from " + self.ip + ":" + str(self.port) + " -> " + " ".join(message))            
                #   JOIN    #
                if message[0] == "JOIN":
                    # join-exist is sent to peer,
                    # if an account with this username already exists
                    if db.is_account_exist(message[1]):
                        response = "join-exist"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)  
                        self.tcpClientSocket.send(response.encode())
                    # join-success is sent to peer,
                    # if an account with this username is not exist, and the account is created
                    else:
                        db.register(message[1], message[2])
                        response = "join-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                #   LOGIN    #
                elif message[0] == "LOGIN":
                    # login-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message[1]):
                        response = "login-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # login-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message[1]):
                        response = "login-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # login-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrievedPass = db.get_password(message[1])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is added to db with its username, port number, and ip address
                        if retrievedPass == message[2]:
                            self.username = message[1]
                            self.lock.acquire()
                            try:
                                tcpThreads[self.username] = self
                            finally:
                                self.lock.release()

                            db.user_login(message[1], self.ip, message[3])
                            # login-success is sent to peer,
                            # and a udp server thread is created for this peer, and thread is started
                            # timer thread of the udp server is started
                            response = "login-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                            self.udpServer = UDPServer(self.username, self.tcpClientSocket)
                            self.udpServer.start()
                            self.udpServer.timer.start()
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "login-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                #   LOGOUT  #
                elif message[0] == "LOGOUT":
                    # if user is online,
                    # removes the user from onlinePeers list
                    # and removes the thread for this user from tcpThreads
                    # socket is closed and timer thread of the udp for this
                    # user is cancelled
                    if len(message) > 1 and message[1] is not None and db.is_account_online(message[1]):
                        db.user_logout(message[1])
                        self.lock.acquire()
                        try:
                            if message[1] in tcpThreads:
                                del tcpThreads[message[1]]
                        finally:
                            self.lock.release()
                        print(self.ip + ":" + str(self.port) + " is logged out")
                        self.tcpClientSocket.close()
                        self.udpServer.timer.cancel()
                        break
                    else:
                        self.tcpClientSocket.close()
                        break

                #  RETRIVE #
                elif message[0] == "RETRIVE":
                    online_peers_cursor = db.retrieve_online()
                    online_peers_list = [peer["username"] for peer in online_peers_cursor]
                    self.tcpClientSocket.send(str(online_peers_list).encode())
                    
                #   SEARCH  #
                elif message[0] == "SEARCH":
                    # checks if an account with the username exists
                    if db.is_account_exist(message[1]):
                        # checks if the account is online
                        # and sends the related response to peer
                        if db.is_account_online(message[1]):
                            peer_info = db.get_peer_ip_port(message[1])
                            response = "search-success " + peer_info[0] + ":" + peer_info[1]
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "search-user-not-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                    # enters if username does not exist 
                    else:
                        response = "search-user-not-found"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 

                
           # CREATE-ROOM
                elif message[0] == "CREATE-ROOM":
                # Ensure the message format is correct
                    if len(message) == 3:
                        room_name = message[1]
                        passcode = message[2]

                        # Check if the room name is unique
                        if not db.is_room_exist(room_name):
                            # Generate a unique room ID (for simplicity, you can use a random number)
                            room_id = randint(1000, 9999)
                            # Create the chat room in the database
                            db.create_room(room_id, room_name, passcode)

                            # Send the success response to the client
                            response = f"create-room-success {room_id}"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "create-room-failure Room with this name already exists"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                            self.tcpClientSocket.send(response.encode())

                # # RETRIEVE-ROOMS
                # elif message[0] == "VIEW_ROOMS":
                #     rooms_list = db.view_rooms()
                #     response = f"retrieve-rooms-success {','.join(rooms_list)}"
                #     logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
                #     self.tcpClientSocket.send(response.encode())
                 
                #  RETRIVE Chat rooms 2#
                elif message[0] == "VIEW_ROOMS":
                    chat_rooms_cursor = db.view_rooms2()
                    chat_rooms_list = [room["room_name"] for room in chat_rooms_cursor]
                    self.tcpClientSocket.send(','.join(chat_rooms_list).encode())
                
                # Join Chat Room
                # Assuming message[1] is the room name and message[2] is the passcode
                elif message[0] == "JOIN-ROOM":
                    room_name = message[1]
                    entered_passcode = message[2]
                    username = message[3]

                    # Retrieve the correct passcode from the database
                    retrieved_passcode = db.get_passcode(room_name)

                    print(f"Room Name: {room_name}")
                    print(f"Entered Passcode: {entered_passcode}")
                    print(f"Retrieved Passcode: {retrieved_passcode}")
                    print(f"Username: {username}")

                    # Compare the entered passcode with the retrieved passcode
                    if retrieved_passcode == entered_passcode:
                        # Passcode is correct, proceed to join the room
                        username = message[3]  # Assuming message[3] is the username
                        result = db.join_room(room_name, entered_passcode, username)

                        if result == "join-room-success":
                            response = "join-room-success"
                            logging.info(f"Send to {self.ip}:{str(self.port)} -> {response}")
                            self.tcpClientSocket.send(response.encode())

                            # Send a welcome message to the user who joined
                            welcome_message = f"Welcome to the chat room, {username}!"
                            self.tcpClientSocket.send(welcome_message.encode())
                            self.tcpClientSocket.send(response.encode())
                        elif result == "join-room-already-member":
                            response = "join-room-already-member"
                            logging.info(f"Send to {self.ip}:{str(self.port)} -> {response}")
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "join-room-error"  # Handle other error cases as needed
                            logging.info(f"Send to {self.ip}:{str(self.port)} -> {response}")
                            self.tcpClientSocket.send(response.encode())
                    else:
                        # Passcode is incorrect
                        response = "join-room-wrong-passcode"
                        logging.info(f"Send to {self.ip}:{str(self.port)} -> {response}")
                        self.tcpClientSocket.send(response.encode())

                elif message[0] == "CHAT":
                    # Assuming message[1] is the room name, and message[2] is the actual chat message
                    room_name = message[1]
                    chat_message = message[2]
                    username = self.username

                    # Broadcast the chat message to all members of the chat room
                    members = db.get_chat_room_members(room_name)
                    print(members)
                    for member in members:
                        if member != username:
                            # Get the IP and port of the recipient member
                            recipient_ip, recipient_port = db.get_peer_ip_port(member)

                            # Send the chat message to the recipient using a separate UDP socket
                            udp_socket = socket(AF_INET, SOCK_DGRAM)
                            udp_socket.sendto(f"MESSAGE {username} in {room_name}: {chat_message}".encode(), (recipient_ip, int(recipient_port)))
                            udp_socket.close()



            except:
                print("Something went wrong")
            #     # VIEW-ROOM-DETAILS
            #     elif message[0] == "VIEW-ROOM-DETAILS":
            #         if len(message) == 2:
            #             room_name = message[1]
            #             room_details = db.view_room_details(room_name)
            #             logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + room_details)
            #             self.tcpClientSocket.send(room_details.encode())
            #         else:
            #             response = "view-room-details-invalid-format"
            #             logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)
            #             self.tcpClientSocket.send(response.encode())
            #             self.tcpClientSocket.send(response.encode())
            # except OSError as oErr:
            #     logging.error("OSError: {0}".format(oErr)) 


    # function for resettin the timeout for the udp timer thread
    def resetTimeout(self):
        self.udpServer.resetTimer()

                            
# implementation of the udp server thread for clients
class UDPServer(threading.Thread):


    # udp server thread initializations
    def __init__(self, username, clientSocket):
        threading.Thread.__init__(self)
        self.username = username
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket
    

    # if hello message is not received before timeout
    # then peer is disconnected
    def waitHelloMessage(self):
        if self.username is not None:
            db.user_logout(self.username)
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        self.tcpClientSocket.close()
        print("Removed " + self.username + " from online peers")

    def run(self):
        udpSocket = socket(AF_INET, SOCK_DGRAM)
        udpSocket.bind((host, portUDP))

        while True:
            try:
                message, clientAddress = udpSocket.recvfrom(1024)
                message = message.decode()

                # Process the chat message
                if message.startswith("MESSAGE"):
                    # Extract information from the chat message
                    _, sender, room_name, chat_message = message.split(' ', 3)

                    # Optionally, you can print or handle the chat message here
                    print(f"Received message from {sender} in {room_name}: {chat_message}")

                    # You can add further logic to broadcast the message to all connected clients
                    # For example, call a method to broadcast the message to members of the chat room

            except socket.timeout:
                # Handle socket timeout if needed
                pass


    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.timer.start()


# tcp and udp server port initializations
print("Registy started...")
port = 15600
portUDP = 15500

# db initialization
db = db.DB()

# gets the ip address of this peer
# first checks to get it for windows devices
# if the device that runs this application is not windows
# it checks to get it for macos devices
hostname=gethostname()
try:
    host=gethostbyname(hostname)
except gaierror:
    import netifaces as ni
    host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']


print("Registry IP address: " + host)
print("Registry port number: " + str(port))

# onlinePeers list for online account
onlinePeers = {}
# accounts list for accounts
accounts = {}
# tcpThreads list for online client's thread
tcpThreads = {}

#tcp and udp socket initializations
tcpSocket = socket(AF_INET, SOCK_STREAM)
udpSocket = socket(AF_INET, SOCK_DGRAM)
tcpSocket.bind((host,port))
udpSocket.bind((host,portUDP))
tcpSocket.listen(5)

# input sockets that are listened
inputs = [tcpSocket, udpSocket]

# log file initialization
logging.basicConfig(filename="registry.log", level=logging.INFO)

# as long as at least a socket exists to listen registry runs
while inputs:

    print("Listening for incoming connections...")
    # monitors for the incoming connections
    readable, writable, exceptional = select.select(inputs, [], [])
    for s in readable:
        # if the message received comes to the tcp socket
        # the connection is accepted and a thread is created for it, and that thread is started
        if s is tcpSocket:
            tcpClientSocket, addr = tcpSocket.accept()
            newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
            newThread.start()
        # if the message received comes to the udp socket
        elif s is udpSocket:
            # received the incoming udp message and parses it
            message, clientAddress = s.recvfrom(1024)
            message = message.decode().split()
            # checks if it is a hello message
            if message[0] == "HELLO":
                # checks if the account that this hello message 
                # is sent from is online
                if message[1] in tcpThreads:
                    # resets the timeout for that peer since the hello message is received
                    tcpThreads[message[1]].resetTimeout()
                    print("Hello is received from " + message[1])
                    logging.info("Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(message))
                    
# registry tcp socket is closed
tcpSocket.close()

