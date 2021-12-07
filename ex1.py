import math
import search
import utils
import json
from random import sample
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
        self.turn = 0  # Saving the current turn to follow the clients' location

        # This section removes any unwanted packages from the initial state
        total_packages = list(initial["packages"].keys())
        wanted_packages = []
        for client in initial["clients"].keys():
            wanted_packages += initial["clients"][client]['packages']
        unwanted_packages = [item for item in total_packages if item not in wanted_packages]
        for unwanted in unwanted_packages:
            initial["packages"].pop(unwanted)

        # This dictionary holds each package as a key and its value is its client
        self.packages_dict = {}
        for client in initial['clients'].keys():
            for p in initial['clients'][client]['packages']:
                self.packages_dict[p] = client

        # This section changes the `drones` part of the initial state:
        # Now holding its current location (2-tuple), and a list of size 2 that keeps the packages names
        # held by the drone
        for drone in initial['drones'].keys():
            location = initial["drones"][drone]
            initial["drones"][drone] = {'location': location, 'current_packages': [None, None]}

        # This section changes the `packages` part of the initial state:
        # Now holding a package's location (2-tuple), and its 'OnGround' state, which takes the values 'OnGround' if the
        # package is on the ground, or `drone_name` if the package is held by a drone called `drone_name`.
        for p in initial['packages'].keys():
            loc = initial['packages'][p]
            initial['packages'][p] = {'location': loc, 'onDrone': 'onGround'}

        initial = json.dumps(initial, sort_keys=True)
        search.Problem.__init__(self, initial)

        """ After running the __init__() function, the `initial` object looks like this:
        {
        'drones': {drone_name: {location: (2-tuple), current_packages: [list of 2 entries]}},
        'packages': {package_name: {location: (2-tuple), 'onDrone': 'OnGround' or drone_name}},
        'clients': {client_name: {path: [list of locations], packages: (tuple of wanted packages)}}
        } """

    def actions(self, state):
        """Returns all the actions that can be executed in the given
        state. The result should be a tuple (or other iterable) of actions
        as defined in the problem description file"""

        dict_state = json.loads(state)

        possible_actions = []
        for drone in dict_state['drones'].keys():
            possible_actions_for_drone = []
            possible_actions_for_drone.extend(self.check_clients_for_single_drone(dict_state, drone))
            if possible_actions_for_drone:  # Prioritize delivering
                possible_actions.append(possible_actions_for_drone)
                continue
            possible_actions_for_drone.extend(self.check_packages_for_single_drone(dict_state, drone))
            if possible_actions_for_drone and not len(dict_state['drones'][drone]['current_packages']):
                # If can't deliver and the drone holds no packages, prioritize picking up packages
                possible_actions.append(possible_actions_for_drone)
                continue
            possible_actions_for_drone.extend(self.check_movement_for_single_drone(dict_state, drone))
            # if (not holding stuff and moved closer to package) or (holding stuff and moved closer to client): accept action
            if sum([bool(item) for item in dict_state['drones'][drone]['current_packages']]) < 2:
                # Allowing to wait only if the drone is not at full package capacity
                possible_actions_for_drone.append(("wait", drone))
            possible_actions.append(possible_actions_for_drone)
        all_possible_actions = list(product(*possible_actions))

        actions_after_pickup_detection = self.detect_multiple_delivers(
            self.detect_multiple_pickups(all_possible_actions))

        # For the big input
        if len(actions_after_pickup_detection) > 1000:
            randomed_actions = sample(actions_after_pickup_detection, len(actions_after_pickup_detection) // 1000)
            important_actions = [ac for ac in randomed_actions if
                                 ('deliver' in [a[0] for a in ac] or 'pick up' in [a[0] for a in ac])]
            if len(important_actions):
                return important_actions
            else:
                return randomed_actions
        else:
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
                    if subaction[2] not in picked_up_packages:
                        picked_up_packages.add(subaction[2])
                    else:
                        remove_list.append(actions[i])
                        break
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
                    if subaction[2] not in picked_up_packages:
                        picked_up_packages.add(subaction[3])
                    else:
                        remove_list.append(actions[i])
                        break
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

        self.turn += 1  # Advance to the next turn, move clients
        return json.dumps(state, sort_keys=True)

    def goal_test(self, state):
        """ Given a state, checks if this is the goal state.
         Returns True if it is, False otherwise."""

        dict_state = json.loads(state)
        if not dict_state["packages"]:  # If no packages are found in the state, all were delivered
            return True
        else:
            return False

    def h(self, node):
        """This is the heuristic. It gets a node (not a state,
        state can be accessed via node.state)
        and returns a goal distance estimate"""

        state = json.loads(node.state)

        # This dictionary holds the state of each drone - how many packages he's going for
        # https://stackoverflow.com/questions/3393431/how-to-count-non-null-elements-in-an-iterable/9629842
        drone_state = {}
        for drone in state['drones'].keys():
            drone_state[drone] = 2 - sum(x is not None for x in state['drones'][drone]['current_packages'])

        heuristic_value = 0

        # Iterate over each package on the map
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
                if min_drone:  # Decrement the number of available spots for packages, if drone exists
                    drone_state[min_drone] -= 1
            else:
                drone_min_dist = 0

            client_package_dist = min([utils.distance(state['packages'][package]['location'], loc) for loc in
                                       state['clients'][self.packages_dict[package]]['path']])

            path_dist = drone_min_dist + client_package_dist
            heuristic_value += path_dist

        return heuristic_value

    def check_packages_for_single_drone(self, state, drone):
        """Checks if a drone is in the same tile as a wanted package.
        If so, return an available action for the drone"""
        available_actions = []  # Holds the available 'pick up' actions
        drone_location = state['drones'][drone]['location']
        for package in state["packages"].keys():
            package_location = state['packages'][package]['location']
            if (drone_location == package_location) and (None in state['drones'][drone][
                'current_packages']) and state['packages'][package][
                'onDrone'] == 'onGround':  # If locations are the same, drone has a free slot and the package is on the ground
                available_actions.append(("pick up", drone, package))
        return available_actions

    def check_movement_for_single_drone(self, state, drone):
        """Checks if a drone can move to neighboring tiles.
        If so, return an available 'move' action for the drone"""
        available_actions = []
        corr = state['drones'][drone]['location']
        if corr[0] != 0 and self.map[corr[0] - 1][corr[1]] == 'P':  # UP
            available_actions.append(("move", drone, (corr[0] - 1, corr[1])))
        if corr[0] != (len(self.map) - 1) and self.map[corr[0] + 1][corr[1]] == 'P':  # DOWN
            available_actions.append(("move", drone, (corr[0] + 1, corr[1])))
        if corr[1] != 0 and self.map[corr[0]][corr[1] - 1] == 'P':  # LEFT
            available_actions.append(("move", drone, (corr[0], corr[1] - 1)))
        if corr[1] != (len(self.map[corr[0]]) - 1) and self.map[corr[0]][corr[1] + 1] == 'P':  # RIGHT
            available_actions.append(("move", drone, (corr[0], corr[1] + 1)))
        return available_actions

    def check_clients_for_single_drone(self, state, drone):
        """Checks if a drone is in the same tile as a client and holds its wanted package.
        If so, return an available 'deliver' action for the drone"""
        available_actions = []
        drone_location = state['drones'][drone]['location']
        for p in state['drones'][drone]['current_packages']:
            if p:
                client = self.packages_dict[p]
                if client:  # If found the client that wants the left package
                    client_loc = state['clients'][client]['path'][self.turn % len(state['clients'][client]['path'])]
                    if drone_location == client_loc:
                        available_actions.append(("deliver", drone, client, p))
        return available_actions


def create_drone_problem(game):
    return DroneProblem(game)
