#!/usr/bin/python2
import socket
import json
import os
import random
import sys
from socket import error as SocketError
import errno
sys.path.append("../..")
import src.game.game_constants as game_consts
from src.game.character import *
from src.game.gamemap import *

# Game map that you can use to query 
gameMap = GameMap()
# --------------------------- SET THIS IS UP -------------------------
teamName = "MinionsOfLong"
# ---------------------------------------------------------------------

def pick1stchar():
    # pick the first character in the team, randomly
    candChar = [char for char in game_consts.classesJson]
    #return i2char[random.randrange(len(i2char))]
    return random.choice(candChar)

def findBestComps(char):
    # Find the best companions for a given char

    #i2char = dict((k,v) for (k,v) in enumerate(game_consts.classesJson))
    comps0 = {
            'Archer':['Druid','Enchanter','Sorcerer','Wizard'],
            'Assassin':['Druid','Enchanter','Sorcerer','Wizard'],
            'Druid':['Paladin','Warrior'],
            'Enchanter':['Paladin','Warrior'],
            'Paladin':['Archer','Assassin'],
            'Sorcerer':['Paladin','Warrior'],
            'Warrior':['Archer','Assassin'],
            'Wizard':['Paladin','Warrior']
            }
    comps1 = {
            'Archer':['Paladin','Warrior'],
            'Assassin':['Paladin','Warrior'],
            'Druid':['Archer','Assassin'],
            'Enchanter':['Archer','Assassin'],
            'Paladin':['Druid','Enchanter','Sorcerer','Wizard'],
            'Sorcerer':['Archer','Assassin'],
            'Warrior':['Druid','Enchanter','Sorcerer','Wizard'],
            'Wizard':['Archer','Assassin']
            }

    # list of candidates
    comp0 = random.choice(comps0[char])
    comp1 = random.choice(comps1[char])

    return comp0,comp1

# Set initial connection data
def initialResponse():
# ------------------------- CHANGE THESE VALUES -----------------------
    char0 = pick1stchar()
    char1,char2 = findBestComps(char0)
    '''
    print('I called this')
    print('char0 = '+char0)
    print('char1 = '+char1)
    print('char2 = '+char2)
    '''
    return {'TeamName': teamName,
            'Characters': [
                {"CharacterName": char0+"0",
                 "ClassId": char0},
                {"CharacterName": char1+"1",
                 "ClassId": char1},
                {"CharacterName": char2+"2",
                 "ClassId": char2},
            ]}
# ---------------------------------------------------------------------

# Determine actions to take on a given turn, given the server response
def processTurn(serverResponse):
# --------------------------- CHANGE THIS SECTION -------------------------
    # Setup helper variables
    actions = []
    myteam = []
    enemyteam = []
    # Find each team and serialize the objects
    for team in serverResponse["Teams"]:
        if team["Id"] == serverResponse["PlayerInfo"]["TeamId"]:
            for characterJson in team["Characters"]:
                character = Character()
                character.serialize(characterJson)
                myteam.append(character)
        else:
            for characterJson in team["Characters"]:
                character = Character()
                character.serialize(characterJson)
                enemyteam.append(character)
# ------------------ You shouldn't change above but you can ---------------

    # Choose a target
    target = findMinHealth(enemyteam)

    # If we found a target
    if target:
        for character in myteam:
            # If I am in range, either move towards target
            if character.in_range_of(target, gameMap):
                # Am I already trying to cast something?
                if character.casting is None:
                    cast = False
                    for abilityId, cooldown in character.abilities.items():
                        # Do I have an ability not on cooldown
                        if cooldown == 0:
                            # If I can, then cast it
                            ability = game_consts.abilitiesList[int(abilityId)]
                            # Get ability
                            actions.append({
                                "Action": "Cast",
                                "CharacterId": character.id,
                                # Am I buffing or debuffing? If buffing, target myself
                                "TargetId": target.id if ability["StatChanges"][0]["Change"] < 0 else character.id,
                                "AbilityId": int(abilityId)
                            })
                            cast = True
                            break
                    # Was I able to cast something? Either wise attack
                    if not cast:
                        actions.append({
                            "Action": "Attack",
                            "CharacterId": character.id,
                            "TargetId": target.id,
                        })
            else: # Not in range, move towards
                actions.append({
                    "Action": "Move",
                    "CharacterId": character.id,
                    "TargetId": target.id,
                })

    # Send actions to the server
    return {
        'TeamName': teamName,
        'Actions': actions
    }

def findMinHealth(enemyteam):
    target = random.choice(enemyteam)
    minHealth = sys.maxint
    for character in enemyteam:
        charHealth = character.attributes.health
        if not character.is_dead() and charHealth < minHealth:
            target = character
    return target

def findToughest(enemyteam):
    target = random.choice(enemyteam)
    minToughness = sys.maxint
    for character in enemyteam:
        charTough = character.attributes.maxHealth*character.attributes.armor
        if not character.is_dead() and charTough < minToughness:
            target = character
    return target

# ---------------------------------------------------------------------

# Main method
# @competitors DO NOT MODIFY
if __name__ == "__main__":
    # Config
    conn = ('localhost', 1337)
    if len(sys.argv) > 2:
        conn = (sys.argv[1], int(sys.argv[2]))

    # Handshake
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(conn)

    # Initial connection
    s.sendall(json.dumps(initialResponse()) + '\n')

    # Initialize test client
    game_running = True
    members = None

    # Run game
    try:
        data = s.recv(1024)
        while len(data) > 0 and game_running:
            value = None
            if "\n" in data:
                data = data.split('\n')
                if len(data) > 1 and data[1] != "":
                    data = data[1]
                    data += s.recv(1024)
                else:
                    value = json.loads(data[0])

                    # Check game status
                    if 'winner' in value:
                        game_running = False

                    # Send next turn (if appropriate)
                    else:
                        msg = processTurn(value) if "PlayerInfo" in value else initialResponse()
                        s.sendall(json.dumps(msg) + '\n')
                        data = s.recv(1024)
            else:
                data += s.recv(1024)
    except SocketError as e:
        if e.errno != errno.ECONNRESET:
            raise  # Not error we are looking for
        pass  # Handle error here.
    s.close()
