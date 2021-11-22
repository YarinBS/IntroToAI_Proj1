import math
import search
import utils
import json
from itertools import product

ids = ["XXXXXXXXX", "XXXXXXXXX"]


class DroneProblem(search.Problem):
    """This class implements a medical problem according to problem description file"""

    def __init__(self, initial):
        """Don't forget to implement the goal test
        You should change the initial to your own representation.
        search.Problem.__init__(self, initial) creates the root node"""

        # Saving the map outside the initial state and removing it from initial
        self.map = initial['map']
        del initial['map']
        self.turn = 0

        # self.packages_dict = {}
        # for client in initial['clients'].keys():
        #     for p in initial['clients'][client]['packages']:
        #         self.packages_dict[p] = client

        # This section removes any unwanted packages from the initial state
        total_packages = list(initial["packages"].keys())
        wanted_packages = []
        for client in initial["clients"].keys():
            wanted_packages += initial["clients"][client]['packages']
        unwanted_packages = [item for item in total_packages if
                             item not in wanted_packages]  # Check if the subtraction is correct
        for unwanted in unwanted_packages:
            initial["packages"].pop(unwanted)

        # This section changes the `drones` part of the initial state:
        # Now holding its current location (2-tuple), and a list of size 2 that keeps the packages names
        # held by the drone
        # all_drones = initial["drones"]  # the dictionary that contain all the drones
        # for drone in all_drones:
        #     location = initial["drones"][drone]
        #     initial["drones"][drone] = {'location': location, 'current_packages': [None, None]}
        for drone in initial['drones'].keys():
            location = initial["drones"][drone]
            initial["drones"][drone] = {'location': location, 'current_packages': [None, None]}

        # This section changes the `clients` part of the initial state:
        # Now holding a client's current location (int with range 0-len(path) - 1), its path (list of 2-tuples), and
        # a tuple with its wanted packages' names
        # for client in initial["clients"].keys():
        #     c_path = initial["clients"][client]["path"]
        #     c_packages = initial["clients"][client]["packages"]
        #     initial["clients"][client] = {'location': 0, 'path': c_path, 'packages': c_packages}

        # This section changes the `packages` part of the initial state:
        # Now holding a package's location (2-tuple), and its 'OnGround' state, which takes the values 'OnGround' if the
        # package is on the ground, or `drone_name` if the package is held by a drone called `drone_name`.
        for p in initial['packages'].keys():
            loc = initial['packages'][p]
            initial['packages'][p] = {'location': loc, 'onDrone': 'onGround'}

        initial = json.dumps(initial, sort_keys=True)
        search.Problem.__init__(self, initial)

        """
        After running the __init__() function, the `initial` object looks like this:
        
        {
        'drones': {drone_name: {location: (2-tuple), current_packages: [list of 2 entries]}},
        'packages': {package_name: {location: (2-tuple), 'onDrone': 'OnGround' or drone_name}},
        'clients': {client_name: {path: [list of locations], packages: (tuple of wanted packages)}}
        }
        """

    def actions(self, state):
        """Returns all the actions that can be executed in the given
        state. The result should be a tuple (or other iterable) of actions
        as defined in the problem description file"""

        dict_state = json.loads(state)

        # --------------------------

        # Implementing Tomer's actions
        possible_actions = []
        for drone in dict_state['drones'].keys():
            possible_actions_for_drone = []
            possible_actions_for_drone.extend(self.check_packages_for_single_drone(dict_state, drone))
            possible_actions_for_drone.extend(self.check_movement_for_single_drone(dict_state, drone))
            possible_actions_for_drone.extend(self.check_clients_for_single_drone(dict_state, drone))
            possible_actions_for_drone.append(("wait", drone))
            possible_actions.append(possible_actions_for_drone)
        all_possible_actions = list(product(*possible_actions))

        # --------------------------

        actions_after_pickup_detection = self.detect_multiple_delivers(
            self.detect_multiple_pickups(all_possible_actions))
        return actions_after_pickup_detection

    def detect_multiple_pickups(self, actions):
        """This function takes a list of actions in the form of [(), (), (), ...]
        and checks if there are 2 'pick up' actions for 2 different drones on the same package.
        If so, it removes this action"""
        remove_list = []
        for i in range(len(actions)):
            picked_up_packages = set()
            for subaction in actions[i]:
                if subaction[0] == 'pick up':
                    if subaction[2] not in picked_up_packages:  # .keys():  # Should be O(n)
                        # if not picked_up_packages.get(subaction[2]):  #Should be O(1): https://www.quora.com/What-is-the-time-complexity-of-checking-if-a-key-is-in-a-dictionary-in-Python
                        # picked_up_packages[subaction[2]] = 1
                        picked_up_packages.add(subaction[2])
                    else:
                        remove_list.append(actions[i])
                        break
        # return list(set(actions) - set(remove_list))
        return [item for item in actions if item not in remove_list]  # Check if this works properly!

    def detect_multiple_delivers(self, actions):
        """This function takes a list of actions in the form of [(), (), (), ...]
        and checks if there are 2 'deliver' actions for 2 different drones on the same package.
        If so, it removes this action"""
        remove_list = []
        for i in range(len(actions)):
            picked_up_packages = set()
            for subaction in actions[i]:
                if subaction[0] == 'deliver':
                    if subaction[2] not in picked_up_packages:  # .keys():  # Should be O(n)
                        # if not picked_up_packages.get(subaction[3]):  #Should be O(1): https://www.quora.com/What-is-the-time-complexity-of-checking-if-a-key-is-in-a-dictionary-in-Python
                        #     picked_up_packages[subaction[3]] = 1
                        picked_up_packages.add(subaction[3])
                    else:
                        remove_list.append(actions[i])
                        break
        # return list(set(actions) - set(remove_list))
        return [item for item in actions if item not in remove_list]  # Check if this works properly!

    def result(self, state, action):
        """Return the state that results from executing the given
        action in the given state. The action must be one of
        self.actions(state)."""
        state = json.loads(state)
        for a in action:
            if a[0] == "move":
                state["drones"][a[1]]['location'] = a[2]
                if state['drones'][a[1]]['current_packages'][0] is not None:
                    left_package = state['drones'][a[1]]['current_packages'][0]
                    state['packages'][left_package]['location'] = a[2]
                elif state['drones'][a[1]]['current_packages'][1] is not None:
                    right_package = state['drones'][a[1]]['current_packages'][1]
                    state['packages'][right_package]['location'] = a[2]
            elif a[0] == "pick up":
                if state["drones"][a[1]]['current_packages'][0] is None:
                    state["drones"][a[1]]['current_packages'][0] = a[2]
                    state['packages'][a[2]]['onDrone'] = a[1]
                elif state["drones"][a[1]]['current_packages'][1] is None:
                    state["drones"][a[1]]['current_packages'][1] = a[2]
                    state['packages'][a[2]]['onDrone'] = a[1]
            elif a[0] == "deliver":
                if state["drones"][a[1]]['current_packages'][0] == a[3]:
                    state["drones"][a[1]]['current_packages'][0] = None
                else:
                    state["drones"][a[1]]['current_packages'][1] = None
                state["packages"].pop(a[3])

        # Moving the clients to the next tile in their path
        # for c in state['clients'].keys():
        #     if state['clients'][c]['location'] == len(state['clients'][c]['path']) - 1:
        #         state['clients'][c]['location'] = 0
        #     else:
        #         state['clients'][c]['location'] += 1

        self.turn += 1

        return json.dumps(state, sort_keys=True)

    def goal_test(self, state):
        """ Given a state, checks if this is the goal state.
         Returns True if it is, False otherwise."""

        """ if there aren't packages, the packages dictionary is empty so the bool value is false, but this is a goal 
        state so we need to return for it true, this is why we did the opposite."""
        dict_state = json.loads(state)
        if not dict_state["packages"]:
            return True
        else:
            return False

    def manhattan_distance(self, state, package_loc):
        """This function calculate the manhattan distance of the closest drone for
         a given package"""
        min_dist = math.inf
        for drone in state['drones']:
            drone_loc = state['drones'][drone]['location']
            dist = sum(abs(val1 - val2) for val1, val2 in zip(package_loc, drone_loc))
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def h(self, node):
        """This is the heuristic. It gets a node (not a state,
        state can be accessed via node.state)
        and returns a goal distance estimate"""

        state = json.loads(node.state)

        # This dictionary holds the state of each drone - how many packages he's
        # going for
        # https://stackoverflow.com/questions/3393431/how-to-count-non-null-elements-in-an-iterable/9629842
        drone_state = {}
        for drone in state['drones'].keys():
            drone_state[drone] = 2 - sum(x is not None for x in state['drones'][drone]['current_packages'])

        # This dictionary holds each package as a key and its value is its client
        packages_dict = {}
        for client in state['clients'].keys():
            for p in state['clients'][client]['packages']:
                packages_dict[p] = client

        # Iterate over each package on the map

        heuristic_value = 0

        for package in state['packages'].keys():
            if state['packages'][package]['onDrone'] == 'onGround':
                # Finding the closest drone which still has room for a package
                drone_min_dist = math.inf
                min_drone = ''
                for drone in state['drones'].keys():
                    if drone_state[drone]:
                        curr_dist = utils.distance(state['packages'][package]['location'],
                                                   state['drones'][drone]['location'])
                        if curr_dist < drone_min_dist:
                            drone_min_dist = curr_dist
                            min_drone = drone
                # Decrement the number of available spots for packages
                if min_drone:
                    drone_state[min_drone] -= 1
            else:
                drone_min_dist = 0

            client_package_dist = min([utils.distance(state['packages'][package]['location'], loc) for loc in
                                       state['clients'][packages_dict[package]]['path']])

            path_dist = drone_min_dist + client_package_dist
            heuristic_value += path_dist

        return heuristic_value

    def check_packages_for_single_drone(self, state, drone):
        """Checks if a drone is in the same tile as a wanted package.
        If so, return an available action for the drone"""
        available_actions = []  # Holds the available 'pick up' actions
        # for drone in state["drones"].keys():
        drone_location = state['drones'][drone]['location']
        for package in state["packages"].keys():
            package_location = state['packages'][package]['location']
            if (drone_location == package_location) and (None in state['drones'][drone][
                'current_packages']) and state['packages'][package][
                'onDrone'] == 'onGround':  # If locations are the same and drone has a free slot
                available_actions.append(("pick up", drone, package))
        return available_actions

    def check_movement_for_single_drone(self, state, drone):
        """Checks if a drone can move to neighboring tiles.
        If so, return an available 'move' action for the drone"""
        available_actions = []
        # for drone in state['drones'].keys():
        corr = state['drones'][drone]['location']
        # UP
        if corr[0] != 0 and self.map[corr[0] - 1][corr[1]] == 'P':
            available_actions.append(("move", drone, (corr[0] - 1, corr[1])))
        # DOWN
        if corr[0] != (len(self.map) - 1) and self.map[corr[0] + 1][corr[1]] == 'P':
            available_actions.append(("move", drone, (corr[0] + 1, corr[1])))
        # LEFT
        if corr[1] != 0 and self.map[corr[0]][corr[1] - 1] == 'P':
            available_actions.append(("move", drone, (corr[0], corr[1] - 1)))
        # RIGHT
        if corr[1] != (len(self.map[corr[0]]) - 1) and self.map[corr[0]][corr[1] + 1] == 'P':
            available_actions.append(("move", drone, (corr[0], corr[1] + 1)))
        return available_actions

    def check_clients_for_single_drone(self, state, drone):
        """Checks if a drone is in the same tile as a client and holds its wanted package.
        If so, return an available 'deliver' action for the drone"""
        available_actions = []
        # for drone in state['drones'].keys():
        drone_location = state['drones'][drone]['location']
        left_package = state['drones'][drone]['current_packages'][0]
        right_package = state['drones'][drone]['current_packages'][1]
        if left_package:  # If holding left package
            client = self.match_package_to_client(state, state['drones'][drone]['current_packages'][0])
            if client:  # If found the client that wants the left package
                # client_corr = state['clients'][client]['path'][state["clients"][client]["location"]]
                client_corr = state['clients'][client]['path'][self.turn % len(state['clients'][client]['path'])]
                if drone_location == client_corr:
                    available_actions.append(("deliver", drone, client, left_package))
        if right_package:  # If holding right package
            client = self.match_package_to_client(state, state['drones'][drone]['current_packages'][1])
            if client:  # If found the client that wants the right package
                # client_corr = state['clients'][client]['path'][state["clients"][client]["location"]]
                client_corr = state['clients'][client]['path'][self.turn % len(state['clients'][client]['path'])]
                if drone_location == client_corr:
                    available_actions.append(("deliver", drone, client, right_package))
        return available_actions

    def match_package_to_client(self, state, package):
        """Looks for the client that requests `package` and returns its name"""
        for client in state["clients"].keys():
            if package in state["clients"][client]['packages']:
                return client
        # return self.packages_dict.get(package)

    """Feel free to add your own functions
    (-2, -2, None) means there was a timeout"""


def create_drone_problem(game):
    return DroneProblem(game)
