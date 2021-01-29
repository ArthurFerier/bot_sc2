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

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts


    async def on_step(self, iteration):
        # Populate this function with whatever your bot should do!

        await self.distribute_workers()

        await self.build_workers()

        await self.build_pylons()

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
        nexus = self.townhalls.ready.random
        position = nexus.position.towards(self.enemy_start_locations[0], 10)

        if (
            # if we have less than 4 spaces left for units
            # todo : verify we are not supply_blocked
                #  => implement good functions to see if it is the case
            self.supply_left < 4 and
            # verify that we are not already building a pylon
            self.already_pending(UnitTypeId.PYLON) == 0 and
            self.can_afford(UnitTypeId.PYLON)
        ):
            await self.build(UnitTypeId.PYLON, near=position)


    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends
