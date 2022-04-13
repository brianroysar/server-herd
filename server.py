import asyncio
import sys
import time
import logging
import requests
import json

API_KEY = "AIzaSyABR_iYdRG2lLQIjfDEZLE76rGAC0vmj-E"

########################### HELPER FUNCTIONS ###########################
def is_valid_client_ID(clientID):
    for c in clientID:
        if (c == " " or c == "\t" or c == "\r" or  c == "\n" or c == "\f" or c == "\v"):
            return False
    return True

# Helper class so we dont log errros in our log file
class OnlyInfoFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('INFO')

# Create URL for API request
def getURL(location, radius, api_key):
    seperating_index = 0
    for i in range(1,len(location)):
        if (location[i] == "+" or location[i] == "-"):
            seperating_index = i
            break
    loc = location[:seperating_index] + "," +location[seperating_index:]
    return "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location="+loc+"&radius="+str(radius)+"&key="+str(api_key)

def isValidRequest(cm):
    if (len(cm) == 0):
        return False
    cms = cm.split()
    if (cms[0] != "IAMAT" and cms[0] != "WHATSAT" and cms[0] != "AT"):
        return False
    if (cms[0] == "IAMAT" or cms[0] == "WHATSAT"):
        if (len(cms) != 4):
            return False
        if (not is_valid_client_ID(cms[1])):
            return False
    return True

def communicatesWith(server_name):
    if (server_name == "Juzang"):
        return ["Clark", "Bernard", "Johnson"]
    elif (server_name == "Bernard"):
        return ["Johnson", "Jaquez", "Juzang"]
    elif (server_name == "Jaquez"):
        return ["Clark", "Bernard"]
    elif (server_name == "Johnson"):
        return ["Juzang", "Bernard"]
    elif (server_name == "Clark"):
        return ["Juzang", "Jaquez"]

def getPortNumber(server_name):
    port_num = 0
    if (server_name == "Juzang"):
        port_num = 10356
    elif (server_name == "Bernard"):
        port_num = 10357
    elif (server_name == "Jaquez"):
        port_num = 10358
    elif (server_name == "Johnson"):
        port_num = 10359
    elif (server_name == "Clark"):
        port_num = 10360
    return port_num

########################### Server class ###########################
class Server:
    def __init__(self, server_name):
        self.server_name = server_name
        self.port_num = getPortNumber(self.server_name)
        self.client_dict = dict()
        self.client_time_dict = dict()
    
    ########################### flood ###########################

    async def flood(self, message):
        for x in communicatesWith(self.server_name):
            try:
                reader, writer = await asyncio.open_connection('127.0.0.1', getPortNumber(x))
                writer.write(message.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except:
                pass

    ########################### activate_server ###########################

    async def activate_server(self):

        # Setting up the log file
        logging.basicConfig(filename = self.server_name + ".log", level=logging.INFO)
        logger = logging.getLogger()
        logger.addFilter(OnlyInfoFilter())

        # Starting server up
        logging.info("Starting up server: " + str(self.server_name))
        server = await asyncio.start_server(self.handle_connection, host = '127.0.0.1', port = self.port_num)

        # Server will continue to run until we tell it to stop
        await server.serve_forever()

        # Close the server upon manual request
        logging.info("Closing server: " + str(self.server_name))
        server.close()

    ########################### handle_connection ###########################
    # either with client or another server 
    async def handle_connection(self, reader, writer):
        # Interpreting the message
        data = await reader.readline()
        client_message = data.decode()

        logging.info("RECEIVED MESSAGE: " + client_message)
        
        # Message to send back to the client
        to_send = ""

        if (not isValidRequest(client_message)):
            to_send = "? " + client_message
        else:
            cm_split = client_message.split()
            option = cm_split[0]
            client_ID = cm_split[1]
        
            ############################# IAMAT OPTION #############################
            if (option == "IAMAT"):
                # Interpreting the message
                lat_long = cm_split[2]
                client_time = cm_split[3]
                server_time = time.time()
                time_diff = server_time - float(client_time)
                
                # Building the message to send back to client
                if (time_diff < 0):
                    to_send = "AT " + self.server_name + " -" + str(time_diff) + " " + client_ID + " "+ lat_long + " " + client_time
                else:
                    to_send = "AT " + self.server_name + " +" + str(time_diff) + " " + client_ID + " "+ lat_long + " " + client_time

                current_time = str(time.time())
                temp_to_send = to_send
                to_send = to_send + " Time: " + current_time
                
                # Storing the most recent to_send details per client_ID
                # logging.info(to_send)

                # Store it also in the dictionary
                self.client_dict[client_ID] = to_send
                self.client_time_dict[client_ID] = current_time
                await self.flood(to_send)
                to_send = temp_to_send

                # print(self.client_dict)

            ############################# WHATSAT OPTION #############################
            elif (option == "WHATSAT"):
                logging.info(self.client_dict)
                # Interpreting the message
                radius_from_client = float(cm_split[2])
                information_upped_bound = int(cm_split[3])  
                
                # Error checking for size limit
                if (radius_from_client > 50):
                    print("Radius is too big (max 50 km)")
                    sys.exit(1)
            
                if (information_upped_bound > 20):
                    print("Information upper bound too big (max 20)")
                    sys.exit(1)
                # print(self.client_dict[client_ID].split())
                # Obtain location indormation from the most current entry
                loc = self.client_dict[client_ID].split()[4]
                
                # Getting the infromation of whats nearby using Google API
                payload = {}
                headers = {}
                # *1000 to convert km to m
                url = getURL(loc, radius_from_client*1000, API_KEY)
                response = requests.request("GET", url, headers=headers, data=payload)
                data = response.json()
                # Enforce upper limit for number of results retrieved
                data["results"] = data["results"][:information_upped_bound]
                # remove the timestamp
                first_line = self.client_dict[client_ID]
                fl_split = first_line.split()
                removed = " ".join(fl_split[0:6])

                to_send = removed + "\n" + str(json.dumps(data, indent=4))
            ############################# AT OPTION #############################
            elif (option == "AT"):
                logging.info("recieved flood")
                to_send = None
                client_ID = cm_split[3]
                proposed_time = cm_split[7]
                if (client_ID in self.client_dict):
                    if (self.client_time_dict[client_ID] < proposed_time):
                        self.client_dict[client_ID] = client_message
                        self.client_time_dict[client_ID] = proposed_time
                        await self.flood(client_message)
                    else:
                        pass       
                else:
                    self.client_dict[client_ID] = client_message
                    self.client_time_dict[client_ID] = proposed_time
                    await self.flood(client_message)
                
        
        if (to_send != None):
            logging.info("Sending to client" + to_send)
            writer.write(to_send.encode())
            await writer.drain()
    
        writer.close()

# server.py will take in one CLI arg which is the server name
# ('Juzang', 'Bernard', 'Jaquez', 'Johnson', 'Clark')
if __name__ == '__main__':

    # Error handling when incorrect # of args
    if (len(sys.argv) != 2):
        print("Incorrect number of arguments")
        sys.exit(1)
    
    server_name = sys.argv[1]
    server = Server(server_name)

    try:
        asyncio.run(server.activate_server())
    except KeyboardInterrupt:
        pass
    
