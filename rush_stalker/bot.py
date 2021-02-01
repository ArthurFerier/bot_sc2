from sc2 import BotAI, Race
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.player import Bot, Computer


class CompetitiveBot(BotAI):
    NAME: str = "CompetitiveBot"
    """This bot's name"""
    RACE: Race = Race.Protoss
    """This bot's Starcraft 2 race.
    Options are:
        Race.Terran
        Race.Zerg
        Race.Protoss
        Race.Random
    """

    # todo : couldn't find the __init__ method to set the sc2.proxy_built = False
    def __init__(self):
        BotAI.__init__(self)
        self.proxy_built = False

    async def on_start(self):
        print("Game started")
        # Do things here before the game starts

    async def on_step(self, iteration):
        # Populate this function with whatever your bot should do!

        # send the worker to collect resources when doing nothing
        await self.distribute_workers()

        # build workers
        # self.do(self.townhalls.idle.first.train(UnitTypeId.SCV)) # not good but I tried
        await self.build_workers()

        await self.build_pylons()

        # useless function
        # await self.build_gateway()

        await self.build_gas()

        await self.build_cyber_core()

        await self.train_stalkers()

        await self.build_four_gates()

        await self.chrono()

        await self.warpgate_research()

        await self.attack()

        await self.warp_stalkers()

        #await self.micro()

        pass

    async def build_workers(self):
        nexus = self.townhalls.ready.random
        if (
                self.can_afford(UnitTypeId.PROBE) and  # UnitTypeId.PROBE = worker
                nexus.is_idle and  # not doing anything and
                # amount of workers < number of townhalls times 22 (22 workers per townhalls is a good mean)
                self.workers.amount < self.townhalls.amount * 22
        ):
            # we are here but no workers are being built ...
            nexus.train(UnitTypeId.PROBE)


    async def build_pylons(self):
        nexus = self.townhalls.ready.random
        position = nexus.position.towards(self.enemy_start_locations[0], 10)

        if (
                # if we have less than 3 spaces left for units
                self.supply_left < 3 and
                # verify that we are not already building a pylon
                self.already_pending(UnitTypeId.PYLON) == 0 and
                self.can_afford(UnitTypeId.PYLON)
        ):
            await self.build(UnitTypeId.PYLON, near=position)

        # build proxy pylon
        # ! proxy_built can be equal to true
        if (
            not self.proxy_built and
            self.structures(UnitTypeId.GATEWAY).amount == 4 and
            self.can_afford(UnitTypeId.PYLON)
        ):
            self.proxy_built = True
            # we start from the middle and we go 20 blocks to the enemy location
            pos = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)
            await self.build(UnitTypeId.PYLON, near=pos)




    # why do I have this function ? ===> four gates
    async def build_gateway(self):
        if (
                self.structures(UnitTypeId.PYLON).ready and
                self.can_afford(UnitTypeId.GATEWAY) and
                # if we don't have a gateway already
                not self.structures(UnitTypeId.GATEWAY)
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            await self.build(UnitTypeId.GATEWAY, near=pylon)

    # noinspection PyTypeChecker
    async def build_gas(self):
        # if we have a gateway => not necessary but so we have like an order of buildings
        if self.structures(UnitTypeId.GATEWAY):
            for nexus in self.townhalls.ready:
                # we don't want to build an assimilator at places that are not close to the nexus
                vgs = self.vespene_geyser.closer_than(15, nexus)
                for vg in vgs:
                    if not self.can_afford(UnitTypeId.ASSIMILATOR):
                        break
                    worker = self.select_build_worker(vg.position)
                    if worker is None:
                        break
                    # if we don't have any gas building
                    # or any gas buildings that are closer than 1 to or vespene geyser
                    if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                        worker.build(UnitTypeId.ASSIMILATOR, vg)
                        # don't know what it is doing
                        # todo : know what it does
                        worker.stop(queue=True)

    async def build_cyber_core(self):
        # we only need to build one cyber core
        # it is the structure needed for the gateways to build stalkers
        if self.structures(UnitTypeId.PYLON).ready:
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            if self.structures(UnitTypeId.GATEWAY).ready:
                # if no cyber core, then build one
                if not self.structures(UnitTypeId.CYBERNETICSCORE):
                    if (
                            self.can_afford(UnitTypeId.CYBERNETICSCORE) and
                            self.already_pending(UnitTypeId.CYBERNETICSCORE) == 0
                    ):
                        await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)

    async def train_stalkers(self):
        # we prefer train stalkers in warpgates
        """
        if self.structures(UnitTypeId.WARPGATE).amount > 0:

            pylon = self.structures(UnitTypeId.PYLON).ready.random
            placement_pos = await self.find_placement(UnitTypeId.STALKER, near=pylon.position)

            for warpgate in self.structures(UnitTypeId.WARPGATE):
                if (
                    self.can_afford(UnitTypeId.STALKER) and
                    warpgate.is_idle
                    # warpgate must not be in cd, taken in account in idle ?
                ):
                    # todo : complete warping => warping is not the good function ?
                    # j'arrive jusque dans cette zone
                    warpgate.warp_in(UnitTypeId.STALKER, position=placement_pos)

        else:
            for gateway in self.structures(UnitTypeId.GATEWAY):
                if (
                        self.can_afford(UnitTypeId.STALKER) and
                        gateway.is_idle
                ):
                    gateway.train(UnitTypeId.STALKER)
        """
        for gateway in self.structures(UnitTypeId.GATEWAY):
            if (
                    self.can_afford(UnitTypeId.STALKER) and
                    gateway.is_idle
            ):
                gateway.train(UnitTypeId.STALKER)




    # build the rest of the gateway for the four gateway strategy
    # (absolutely no idea of the strategy in question)
    async def build_four_gates(self):
        if (
                self.structures(UnitTypeId.PYLON).ready and
                self.can_afford(UnitTypeId.GATEWAY) and
                self.structures(UnitTypeId.GATEWAY).amount
                # wo that it won't continue to build gateways
                # if they are trasformed into warpgates
                + self.structures(UnitTypeId.WARPGATE).amount < 4
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            await self.build(UnitTypeId.GATEWAY, near=pylon)

    # to use the chrono boost of the protoss when we have energy
    # when we have nothing, we want to chrono boost the nexus to build workers
    # then, when the cybercore is researching, we will boost it
    # then we want to chrono boost our army to build it faster => not implemented yet
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

    async def warpgate_research(self):
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE).ready and
                self.can_afford(AbilityId.RESEARCH_WARPGATE) and
                self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 0
        ):
            cybercore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
            cybercore.research(UpgradeId.WARPGATERESEARCH)

    async def attack(self):
        # changed the method to make the stalkers attack if
        # they are 7 idle instead au 5 in total
        stalkercount = self.units(UnitTypeId.STALKER).amount
        stalkers = self.units(UnitTypeId.STALKER).ready

        if stalkercount > 6:
            for stalker in stalkers:
                stalker.attack(self.enemy_start_locations[0])
        else:
            if self.structures(UnitTypeId.PYLON).ready:
                proxy = self.structures(UnitTypeId.PYLON).closest_to(self.enemy_start_locations[0])
                proxyposition = proxy.position.random_on_distance(3)
                for stalker in stalkers:
                    stalker.attack(proxyposition)


    async def warp_stalkers(self):
        for warpgate in self.structures(UnitTypeId.WARPGATE).ready:
            abilities = await self.get_available_abilities(warpgate)
            proxy = self.structures(UnitTypeId.PYLON).closest_to(self.enemy_start_locations[0])
            if (
                AbilityId.WARPGATETRAIN_STALKER in abilities and
                self.can_afford(UnitTypeId.STALKER)
            ):
                placement = proxy.position.random_on_distance(3)
                warpgate.warp_in(UnitTypeId.STALKER, placement)


    # a bit cheating against real person I think
    async def micro(self):
        stalkers = self.units(UnitTypeId.STALKER)
        enemy_location = self.enemy_start_locations[0]

        if (
            self.structures(UnitTypeId.PYLON).ready
        ):
            pylon = self.structures(UnitTypeId.PYLON).closest_to(enemy_location)

            for stalker in stalkers:
                if stalker.weapon_cooldown == 0:
                    stalker.attack(enemy_location)
                elif stalker.weapon_cooldown < 0:
                     stalker.move(pylon)
                else:
                    stalker.move(pylon)


    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends
