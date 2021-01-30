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

        await self.build_cyber_core()

        await self.build_first_expansion()

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
            # todo : verify we are not supply_blocked
                #  => implement good functions to see if it is the case
            self.supply_left < 5 + int(self.time/60) and
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
    async def find_pylon_pos(self, nexus):
        if self.number_pylons == 0:
            postion_to_en = nexus.position.towards(self.enemy_start_locations[0], 10)
            pos = await self.find_placement(UnitTypeId.PYLON, near=postion_to_en)
            return pos

        for i in range(20):
            # todo : verify parameters
            # we want to spread the pylons
            # and not in the way of the workers gathering minerals
            pos = nexus.position.random_on_distance([10, 15])
            pylons = self.units(UnitTypeId.PYLON)
            if pylons.amount == 0:
                return pos
            if pos.distance_to_closest(pylons) > 10:
                return pos

        return pos

    async def distance_to_nexus(self, position):
        nexus = self.townhalls.closest_to(position)
        return nexus.position.distance_to_point2(position)

    async def build_gateways(self):
        # build first gateway
        if (
            self.structures(UnitTypeId.PYLON).ready
            and self.can_afford(UnitTypeId.GATEWAY)
            and self.structures(UnitTypeId.GATEWAY).amount < 1
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
                        worker = self.workers\
                            .filter(lambda worker: worker.is_collecting or worker.is_idle)\
                            .closest_to(vgg.position)

                        if worker is None:
                            break
                        if not self.gas_buildings or not self.gas_buildings.closer_than(1, vgg):
                            worker.build(UnitTypeId.ASSIMILATOR, vgg)
                            worker.stop(queue=True)


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
                pylon = self.structures(UnitTypeId.PYLON)\
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


    async def build_first_expansion(self):
        if(
            self.structures(UnitTypeId.CYBERNETICSCORE)
            and self.townhalls.amount == 1
            and not self.already_pending(UnitTypeId.NEXUS)
        ):
            if self.can_afford(UnitTypeId.NEXUS):
                await self.expand_now(building=UnitTypeId.NEXUS)
                self.can_construct = True
            else:
                self.can_construct = False







    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends
