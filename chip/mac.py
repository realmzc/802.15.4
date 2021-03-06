import logging
import numbers
import random
import math
from enum import Enum

import chip.bit as bit
import chip.phy
import chip.mlme as mlme
import chip.mcps as mcps
from chip.phy import constants as phyConst

class status( Enum):
    SUCCESS              =  1
    FAILURE              =  0
    INVALID_PARAMETER    = -1

    """MLME-SET.confirm status"""
    READ_ONLY             = -2
    UNSUPPORTED_ATTRIBUTE = -3
    INVALID_INDEX         = -4

    LIMIT_REACHED         = -5
    NO_BEACON             = -6
    SCAN_IN_PROGRESS      = -7
    COUNTER_ERROR         = -8
    FRAME_TOO_LONG        = -9
    UNAVAILABLE_KEY       = -10
    UNSUPPORTED_SECURITY  = -11


class scanType( Enum):
    ED      = 0
    ACTIVE  = 1
    PASSIVE = 2
    ORPHAN  = 3

class constants:
    """MAC layer constants"""
    aBaseSlotDuration         = 60
    aGTSDescPersistenceTime   = 4
    aMaxBeaconOverhead        = 75
    aMaxLostBeacons           = 4
    aMaxMPDUUnsecuredOverhead = 25
    aMaxSIFSFrameSize         = 18
    aMinCAPLength             = 440
    aMinMPDUOverhead          = 9
    aNumSuperframeSlots       = 16
    aUnitBackoffPeriod        = 20
    # constants derived from previous consts
    aBaseSuperframeDuration   = aBaseSlotDuration * aNumSuperframeSlots
    aMaxBeaconPayloadLength   = phyConst.aMaxPHYPacketSize - aMaxBeaconOverhead
    aMaxMACSafePayloadSize    = phyConst.aMaxPHYPacketSize - aMaxMPDUUnsecuredOverhead
    aMaxMACPayloadSize        = phyConst.aMaxPHYPacketSize - aMinMPDUOverhead
    

class Mac:
    def __init__( self, phy):
        self.phy = phy
        # ackWaitDuration = constants.aUnitBackoffPeriod + \
        #                   phyConst.aTurnaroundTime + \
        #                   self.phy.pib['phySHRDuration'] + \
        #                   math.ceil( 6 * self.phy.pib['phySymbolsPerOctet'])
        # # calculate default value, based on defaluts
        # # proper formulas are in comments
        # # m = min( macMaxBE - macMinBE, macMaxCSMABackoffs)
        # m = min( 5 - 3, 4)
        # sum = 0
        # for k in range( m):
        #     # sum += 2 ** ( macMinBE + k)
        #     sum += 2 ** ( 3 + k)
        # # maxFrameTotalWaitTime = ( sum + \
        # #                           ( ( 2 ** macMinBE - 1) * \
        # #                             ( macMaxCSMABackoffs - m))) * constants.aUnitBackoffPeriod + self.phy.pib.phyMaxFrameDuration
        # maxFrameTotalWaitTime = ( sum + \
        #                           ( ( 2 ** 3 - 1) * \
        #                             ( 4 - m))) * constants.aUnitBackoffPeriod + self.phy.pib['phyMaxFrameDuration']
        
        # if self.phy.kind == chip.phy.phyType.UWB:
        #     raise BaseExeption

        self._setDefaultPIB()

    def _setDefaultPIB( self):
        self.pib = { # key: [ value, lower, upper]
            'macExtendedAddress':           [ None, int( '0x0000000000000001', 16), int( '0xfffffffffffffffe', 16)],
            'macAckWaitDuration':           [ None, 0, 0],
            'macAssociatedPANCoord':        [ False, False, True],
            'macAssociationPermit':         [ False, False, True],
            'macAutoRequest':               [ True, False, True],
            'macBattLifeExt':               [ False, False, True],
            'macBattLifeExtPeriods':        [ None, 6, 41],
            'macBeaconPayload':             [ None, 0, 2 ** ( 8 * constants.aMaxBeaconPayloadLength)],
            'macBeaconPayloadLength':       [ 0, 0, constants.aMaxBeaconPayloadLength],
            'macBeaconOrder':               [ 15, 0, 15],
            'macBeaconTxTime':              [ int( '0x000000', 16), int( '0x000000', 16), int( '0xffffff', 16)],
            'macBSN':                       [ random.randint( 0, int( '0xff', 16) + 1), int( '0x00', 16), int( '0xff', 16)], 
            'macCoordExtendedAddress':      [ None, int( '0x0000000000000001', 16), int( '0xfffffffffffffffe', 16)],
            'macCoordShortAddress':         [ int( '0xffff', 16), int( '0x0000', 16), int( '0xffff', 16)],
            'macDSN':                       [ random.randint( 0, int( '0xff', 16) + 1), int( '0x00', 16), int( '0xff', 16)],
            'macGTSPermit':                 [ True, False, True],
            'macMaxBE':                     [ 5, 3, 8],
            'macMaxCSMABackoffs':           [ 4, 0, 5],
            'macMaxFrameTotalWaitTime':     [ None, None, None],
            'macMaxFrameRetries':           [ 3, 0, 7],
            'macMinBE':                     [ 3, 0, 5],
            'macLIFSPeriod':                [ None, None, None],
            'macSIFSPeriod':                [ None, None, None],
            'macPANId':                     [ int( '0xffff', 16), int( '0x0000', 16), int( '0xffff', 16)],
            'macPromiscuousMode':           [ False, False, True],
            'macRangingSupported':          [ False, False, True],
            'macResponseWaitTime':          [ 32, 2, 64],
            'macRxOnWhenIdle':              [ False, False, True],
            'macSecurityEnabled':           [ False, False, True],
            'macShortAddress':              [ int( '0xffff', 16), int( '0x0000', 16), int( '0xffff', 16)],
            'macSuperframeOrder':           [ 15, 0, 15],
            'macSyncSymbolOffset':          [ None, None, None],
            'macTimestampSupported':        [ False, False, True],
            'macTransactionPersistenceTime':[ int( '0x01f4', 16), int( '0x0000', 16), int( '0xffff', 16)],
            'macTxControlActiveDuration':   [ None, 0, 100000],
            'macTxControlPauseDuration':    [ None, 0, 100000],
            'macTxTotalDuration':           [ 0, int( '0x0', 16), int( '0xffffffff', 16)]
        }

    def _set_pib_attr( self, attribute, value):
        if self.pib[attribute][1] <= value <= self.pib[attribute][2]:
            self.pib[attribute][0] = value
            return status.SUCCESS
        else:
            return status.INVALID_PARAMETER

    def _ed_scan( self):
        pass

    def _passive_active_scan( self, scan_type):
        for channel in channels:
            if scan_type == scanType.ACTIVE:
                pass
                # TODO: Tx Beacon request
                
            # TODO: Rx Beacon
            # TODO: Rx Beacon

    def _orphan_scan( self):
        pass


    def _mpdu( self, mhr, payload, mfr):
        pass

    def _mhr( self, frame_ctrl, seq_num, addr, shr):
        pass


    def _fcs( self, data):
        # G16(x) = x^16 + x^12 + x^5 + 1
        gen = 2 ** 16 + 2 ** 12 + 2 ** 5 + 1
        # multiply by x^16
        data <<= 16

        # divide data by G16(x)
        # no need to check if degree of data si higher since
        # we multiply it by x^16
        q  = 0
        dN = bit.len( data) - 1
        dD = bit.len( gen) - 1
        while dN >= dD:
            d = gen << ( dN - dD)
            data ^= d
            dN = bit.len( data) - 1
        
        # we are interested only in the rest
        return data

    def command( self, primitive):
        if   isinstance( primitive, mlme.reset.request):
            logging.debug( "MAC received: MLME-RESET.request")
            if primitive.SetDefaultPIB:
                logging.debug( "MAC resseting to default PIB")
            else:
                logging.debug( "MAC reseting with preserved PIB")
            
            # Wait for reset complete
            return mlme.reset.confirm( status.SUCCESS)

        elif isinstance( primitive, mlme.set.request):
            logging.debug( 'MAC received: MLME-SET.request( {0}, {1})'.format( primitive.PIBAttribute, primitive.PIBAttributeValue))

            # check if attribute exists
            if primitive.PIBAttribute not in self.pib:
                return mlme.set.confirm( status.UNSUPPORTED_ATTRIBUTE, primitive.PIBAttribute)

            # check if attribute is read only
            if primitive.PIBAttribute in ["macExtendedAddress",
                                          "macCoordExtendedAddress",
                                          "macMaxFrameTotalWaitTime",
                                          "macLIFSPeriod",
                                          "macSIFSPeriod",
                                          "macRangingSupported",
                                          "macTimestampSupported"]:
                return mlme.set.confirm( status.READ_ONLY, primitive.PIBAttribute)
            
            return mlme.set.confirm( self._set_pib_attr( primitive.PIBAttribute,
                                                         primitive.PIBAttributeValue),
                                     primitive.PIBAttribute)

                    
        elif isinstance( primitive, mlme.get.request):
            logging.debug( 'MAC received: MLME-GET.request( {0})'.format( primitive.PIBAttribute))
            if primitive.PIBAttribute not in self.pib:
                return mlme.get.confirm( status.UNSUPPORTED_ATTRIBUTE,
                                         primitive.PIBAttribute,
                                         None)
            else:
                return mlme.get.confirm( status.SUCCESS,
                                         primitive.PIBAttribute,
                                         self.pib[primitive.PIBAttribute][0])

#        elif isinstance( primitive, mcps):
#            pass
        else:
            raise BaseException
