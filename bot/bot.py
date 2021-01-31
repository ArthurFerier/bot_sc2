from sc2 import BotAI, Race
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.player import Bot, Computer


class CompetitiveBot(BotAI):
    NAME: str = "Protoss_order_build"
    RACE: Race = Race.Protoss

    """
    
    build order : https://lotv.spawningtool.com/build/96261/
    => to adapt for the IA who can do things faster 
    => when the base is done : relax the rules by giving the choices to the 
    IA by machine learning
    => this build is set to counter terran
    
    what I do not need to care for because IA : 
    
    - build pytons to get supplyblocked => just need to fin the right amount of supply before building ??
    - build workers
    
    """

    def __init__(self):
        BotAI.__init__(self)
        self.number_pylons = 0
        self.can_construct = True
        self.can_train = True

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

    async def on_step(self, iteration):
        # Populate this function with whatever your bot should do!

        await self.distribute_workers()
        await self.build_workers()

        await self.build_gateways()

        await self.build_pylons()
        await self.build_vespene()

        await self.chrono()

        await self.build_cyber_core()
        await self.warp_research()

        await self.build_first_expansion()

        await self.train_stalkers()
        await self.standby_army()

        pass

    # fine function, I don't think there is anything to add (because of the distribute workers)
    async def build_workers(self):
        nexus = self.townhalls.ready.random
        if (
                self.can_afford(UnitTypeId.PROBE) and  # UnitTypeId.PROBE = worker
                nexus.is_idle and  # not doing anything and
                # amount of workers < number of townhalls times 22 (22 workers per townhalls is a good mean)
                self.workers.amount < self.townhalls.amount * 22
        ):
            nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self):

        if (
                # if we have less than 4 spaces left for units
                #  => implement good functions to see if it is the case
                self.supply_left < 5 + int(self.time / 60) and
                # verify that we are not already building a pylon
                self.already_pending(UnitTypeId.PYLON) == 0 and
                self.can_afford(UnitTypeId.PYLON) and
                # supply_cap at 200
                self.supply_cap < 200
        ):
            nexus = self.townhalls.ready.random
            position = await self.find_pylon_pos(nexus)
            await self.build(UnitTypeId.PYLON, near=position)
            self.number_pylons += 1

    # have to ameliorate in the future
    # todo : verify that everything is correct when building lot of pylons
    async def find_pylon_pos(self, nexus):
        if self.number_pylons == 0:
            postion_to_en = nexus.position.towards(self.enemy_start_locations[0], 10)
            pos = await self.find_placement(UnitTypeId.PYLON, near=postion_to_en)
            return pos

        # finding the nexus who needs pylons the most
        # assuming the order is the order of built
        nexuses = self.townhalls.ready
        pylons_near = [0] * nexuses.amount
        for pylon in self.structures(UnitTypeId.PYLON).ready:
            # get id of the closest nexus of the pylon
            nexus_id = pylon.position.sort_by_distance(nexuses)[0]
            for j in range(nexuses.amount):
                if nexus_id == nexuses[j]:
                    pylons_near[j] += 1

        # now I have an unordered list of the number of pylons for each nexus
        poorest_n = 1000
        poorest_pos = 0
        for i in range(len(pylons_near)):
            if pylons_near[i] < poorest_n:
                poorest_pos = i
                poorest_n = pylons_near[i]

        nexus = nexuses[poorest_pos]

        pos = nexus.position.random_on_distance([8, 15])
        for i in range(20):
            await self.chat_send("essai n {}".format(i))
            # we want to spread the pylons
            # and not in the way of the workers gathering minerals

            pylons = self.units(UnitTypeId.PYLON)
            if pylons.amount == 0:
                return pos
            if pos.distance_to_closest(pylons) > 15:
                return pos
            pos = nexus.position.random_on_distance([8, 15])
        await self.chat_send("les 20 positions n'ont pas été un succès")
        return pos

    async def distance_to_nexus(self, position):
        nexus = self.townhalls.closest_to(position)
        return nexus.position.distance_to_point2(position)

    async def build_gateways(self):
        # build first gateway
        if (
            self.structures(UnitTypeId.PYLON).ready
            and self.can_afford(UnitTypeId.GATEWAY)
            and self.structures(UnitTypeId.GATEWAY).amount
            + self.structures(UnitTypeId.WARPGATE).amount < 1
            and self.can_construct
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            position = pylon.position.random_on_distance((0, 6))  # askip 6.5 from liquidpedia
            await self.build(UnitTypeId.GATEWAY, near=position)

    async def build_vespene(self):
        if (
                # build order : for the first assimilator
                self.structures(UnitTypeId.PYLON)
                and self.structures(UnitTypeId.GATEWAY)
                and self.can_afford(UnitTypeId.ASSIMILATOR)
                and self.can_construct
        ):
            # check if there are not already 2 assimilators per nexuses
            if self.structures(UnitTypeId.ASSIMILATOR).amount < self.townhalls.ready.amount * 2:
                for nexus in self.townhalls.ready:
                    vggs = self.vespene_geyser.closer_than(15, nexus)
                    for vgg in vggs:
                        worker = self.workers \
                            .filter(lambda worker: worker.is_collecting or worker.is_idle) \
                            .closest_to(vgg.position)

                        if worker is None:
                            break
                        if not self.gas_buildings or not self.gas_buildings.closer_than(1, vgg):
                            worker.build(UnitTypeId.ASSIMILATOR, vgg)
                            worker.stop(queue=True)

    # todo : improve the overall
    async def chrono(self):
        if self.structures(UnitTypeId.PYLON):
            nexus = self.townhalls.ready.random
            if nexus.energy > 50:
                if (
                        self.structures(UnitTypeId.CYBERNETICSCORE).ready
                ):
                    # we want to boost it while he is not idle
                    if not self.structures(UnitTypeId.CYBERNETICSCORE).ready.idle:
                        cybercore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.random
                        nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, cybercore)
                    else:
                        # the conditions are fine, the prob is here under
                        gateways = self.structures(UnitTypeId.GATEWAY).ready
                        for gateway in gateways:
                            # if there is a gateway that is not idle
                            if not gateway.is_idle:
                                nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, gateway)

                else:
                    if self.structures(UnitTypeId.PYLON).amount > 0:
                        nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)

    async def build_cyber_core(self):
        if (
                self.structures(UnitTypeId.ASSIMILATOR)
                and not self.structures(UnitTypeId.CYBERNETICSCORE)
                and not self.already_pending(UnitTypeId.CYBERNETICSCORE)
        ):
            if (
                    self.can_afford(UnitTypeId.CYBERNETICSCORE)
            ):
                # I want ot build the cybercore the furthest possible from the enemy
                pylon = self.structures(UnitTypeId.PYLON) \
                    .ready.furthest_to(self.enemy_start_locations[0])
                position = pylon.position.random_on_distance((0, 6))

                # we will try a hundred times before giving up
                for i in range(100):
                    if await self.distance_to_nexus(position) > 4:
                        await self.build(UnitTypeId.CYBERNETICSCORE, near=position)
                        self.can_construct = True
                        return
                    position = pylon.position.random_on_distance((0, 6))

                await self.build(UnitTypeId.CYBERNETICSCORE, near=position)
                self.can_construct = True

            else:
                # waiting to have enough money to construct the cybernetics
                self.can_construct = False

    async def warp_research(self):
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE).ready
                and not self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH)
        ):
            if (
                    self.can_afford(AbilityId.RESEARCH_WARPGATE)
            ):
                cybercore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
                cybercore.research(UpgradeId.WARPGATERESEARCH)

                self.can_construct = True
            else:
                self.can_construct = False

    async def build_first_expansion(self):
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE)
                and self.townhalls.amount == 1
                and not self.already_pending(UnitTypeId.NEXUS)
        ):
            if self.can_afford(UnitTypeId.NEXUS):
                await self.expand_now(building=UnitTypeId.NEXUS)
                self.can_construct = True
            else:
                self.can_construct = False

    async def train_stalkers(self):
        # build first two stalkers
        for getaway in self.structures(UnitTypeId.GATEWAY).ready:
            print("we are here")

            if(
                self.can_train
                and self.townhalls.amount == 2
                and self.units(UnitTypeId.STALKER).amount < 2
                and self.can_afford(UnitTypeId.STALKER)
                and getaway.is_idle
            ):
                print("do we arrive here ?")
                getaway.train(UnitTypeId.STALKER)

    # todo : improve this function
    async def standby_army(self):
        town_to_defend = self.townhalls.closest_to(self.enemy_start_locations[0])
        #position = town_to_defend.position.towards(self.enemy_start_locations[0], 9)
        position = self.main_base_ramp.top_center
        for stalker in self.units(UnitTypeId.STALKER):
            stalker.attack(position)





    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends
