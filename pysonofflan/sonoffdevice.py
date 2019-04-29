"""
pysonofflan
Python library supporting Sonoff Smart Devices (Basic/S20/Touch) in LAN Mode.
"""
import asyncio
import json
import logging
from typing import Callable, Awaitable, Dict

import traceback
import websockets

from .client import SonoffLANModeClient


class SonoffDevice(object):
    def __init__(self,
                 host: str,
                 callback_after_update: Callable[..., Awaitable[None]] = None,
                 shared_state: Dict = None,
                 logger=None,
                 loop=None,
                 ping_interval=SonoffLANModeClient.DEFAULT_PING_INTERVAL,
                 timeout=SonoffLANModeClient.DEFAULT_TIMEOUT,
                 context: str = None) -> None:
        """
        Create a new SonoffDevice instance.

        :param str host: host name or ip address on which the device listens
        :param context: optional child ID for context in a parent device
        """
        self.callback_after_update = callback_after_update
        self.host = host
        self.context = context
        self.shared_state = shared_state
        self.basic_info = None
        self.params = {}
        self.params_updated_event = None
        self.loop = loop
        self.tasks = []                                                 # store the tasks that this module create s in a sequence
        self.new_loop = False                                           # use to decide if we should shutdown the loop on exit
        self.messages_received = 0

        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        try:
            if self.loop is None:

                self.new_loop = True
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            self.logger.debug(
                'Initializing SonoffLANModeClient class in SonoffDevice')
            self.client = SonoffLANModeClient(
                host,
                self.handle_message,
                ping_interval=ping_interval,
                timeout=timeout,
                logger=self.logger
            )

            self.message_ping_event = asyncio.Event()
            self.message_acknowledged_event = asyncio.Event()
            self.params_updated_event = asyncio.Event()

            self.tasks.append(self.loop.create_task(self.send_updated_params_loop()))
                        
            self.tasks.append(self.loop.create_task(self.send_availability_loop()))
            
            self.setup_connection_task = self.loop.create_task(self.setup_connection(not self.new_loop))
            self.tasks.append(self.setup_connection_task)

            if self.new_loop:
                self.loop.run_until_complete(self.setup_connection_task)

        except asyncio.CancelledError:
            self.logger.debug('SonoffDevice loop ended, returning')

    async def setup_connection(self, retry):
        self.logger.debug('setup_connection is active on the event loop')
                                    
        retry_count = 0
    
        while True:                                                                                   
            connected = False
            try:
                self.logger.debug('setup_connection yielding to connect()')
                await self.client.connect()
                self.logger.debug(
                    'setup_connection yielding to send_online_message()')
                await self.client.send_online_message()

                connected = True

            except websockets.InvalidMessage as ex:
                self.logger.warn('Unable to connect: %s' % ex)   
                await self.wait_before_retry(retry_count)               
            except ConnectionRefusedError:
                self.logger.warn('Unable to connect: connection refused')                                                                     
                await self.wait_before_retry(retry_count)    
            except websockets.exceptions.ConnectionClosed:
                self.logger.warn('Connection closed unexpectedly during setup')
                await self.wait_before_retry(retry_count)
            except OSError as ex:
                self.logger.warn('OSError in setup_connection(): %s', format(ex) )
                await self.wait_before_retry(retry_count)    
            except Exception as ex:
                self.logger.error('Unexpected error in setup_connection(): %s', format(ex) )
                await self.wait_before_retry(retry_count)

            if connected:
                retry_count = 0                                                                     # reset retry count after successful connection
                try: 
                    self.logger.debug(
                        'setup_connection yielding to receive_message_loop()')
                    await self.client.receive_message_loop()
                                                                                    
                except websockets.InvalidMessage as ex:
                    self.logger.warn('Unable to connect: %s' % ex)
                except websockets.exceptions.ConnectionClosed:
                    self.logger.warn('Connection closed in receive_message_loop()')
                except OSError as ex:
                    self.logger.warn('OSError in receive_message_loop(): %s', format(ex) )
                
                except asyncio.CancelledError:
                    self.logger.debug('receive_message_loop() cancelled' )
                    break

                except Exception as ex:
                    self.logger.error('Unexpected error in receive_message_loop(): %s', format(ex) )
                
                finally:
                    self.message_ping_event.set() 
                    self.logger.debug('finally: closing websocket from setup_connection')
                    await self.client.close_connection()

            if not retry:
                break    

            retry_count +=1

        self.shutdown_event_loop()
        self.logger.debug('exiting setup_connection()')

    async def wait_before_retry(self, retry_count):

        try:

            wait_times = [0.5,1,2,5,10,30,60]                                   # increasing backoff each retry attempt

            if retry_count >= len(wait_times):
                retry_count = len(wait_times) -1

            wait_time = wait_times[retry_count]

            self.logger.debug('Waiting %i seconds before retry', wait_time)

            await asyncio.sleep(wait_time)

        except Exception as ex:
            self.logger.error('Unexpected error in wait_before_retry(): %s', format(ex) )
                
    async def send_availability_loop(self):

        try:
            while True:
                await self.client.disconnected_event.wait()

                if self.callback_after_update is not None:
                    await self.callback_after_update(self)
                    self.client.disconnected_event.clear()
        finally:
            self.logger.debug('exiting send_availability_loop()')

    async def send_updated_params_loop(self):
        self.logger.debug(
            'send_updated_params_loop is active on the event loop')

        try:

            self.logger.debug(
                'Starting loop waiting for device params to change')

            while True:                                                     
                self.logger.debug(
                    'send_updated_params_loop now awaiting event')

                await self.params_updated_event.wait()
                
                await self.client.connected_event.wait()
                self.logger.debug('Connected!')                

                update_message = self.client.get_update_payload(
                    self.device_id,
                    self.params
                )

                try:
                    self.message_ping_event.clear()
                    self.message_acknowledged_event.clear()
                    await self.client.send(update_message)                    

                    await asyncio.wait_for(self.message_ping_event.wait(), 2)
 
                    if self.message_acknowledged_event.is_set():
                        self.params_updated_event.clear() 
                        self.logger.debug('Update message sent, event cleared, should '
                                    'loop now')
                    else:
                        self.logger.warn(
                            "we didn't get an acknowledge message, we have probably been disconnected!")
                                                                                # message 'ping', but not an acknowledgement, so loop
                                                                                # if we were disconnected we will wait for reconnection
                                                                                # if it was another type of message, we will resend change


                except websockets.exceptions.ConnectionClosed:                                   
                    self.logger.error('Connection closed unexpectedly in send()')
                except asyncio.TimeoutError:                     
                    self.logger.warn('Update message not received, close connection, then loop')
                    await self.client.close_connection()                                        # closing connection causes cascade failure in setup_connection and reconnect
                except OSError as ex:
                    self.logger.warn('OSError in send(): %s', format(ex) )

                except asyncio.CancelledError:
                    self.logger.debug('send_updated_params_loop cancelled')
                    break

                except Exception as ex:
                    self.logger.error('Unexpected error in send(): %s', format(ex) )

        except asyncio.CancelledError:
            self.logger.debug('send_updated_params_loop cancelled')

        except Exception as ex:
            self.logger.error('Unexpected error in send(): %s', format(ex) )

        finally:
            self.logger.debug('send_updated_params_loop finally block reached')

    def update_params(self, params):
        self.logger.debug(
            'Scheduling params update message to device: %s' % params
        )    
        self.params = params
        self.params_updated_event.set()

    async def handle_message(self, message):
        """
        Receive message sent by the device and handle it, either updating
        state or storing basic device info
        """
        
        self.messages_received +=1                          # ensure debug messages are unique to stop deduplication by logger 
        self.message_ping_event.set() 

        response = json.loads(message)

        if (
            ('error' in response and response['error'] == 0)
            and 'deviceid' in response
        ):
            self.logger.debug(
                'Message: %i: Received basic device info, storing in instance', self.messages_received)
            self.basic_info = response

            if self.client.connected_event.is_set():        # only mark message as accepted if we are already online (otherwise this is an initial connection message)
                self.message_acknowledged_event.set()           
 
                if self.callback_after_update is not None:
                    await self.callback_after_update(self)

        elif 'action' in response and response['action'] == "update":
 
            self.logger.debug(
                'Message: %i: Received update from device, updating internal state to: %s'
                , self.messages_received , response['params']  )

            if not self.client.connected_event.is_set():
                self.client.connected_event.set()
                self.client.disconnected_event.clear()
                send_update = True

            if not self.params_updated_event.is_set():      # only update internal state if there is not a new message queued to be sent
                
                if self.params != response['params']:       # only send client update message if there is a change
                    self.params = response['params']
                    send_update = True

            if send_update and self.callback_after_update is not None:
                await self.callback_after_update(self)

        else:
            self.logger.error(
                'Unknown message received from device: ' % message)
            raise Exception('Unknown message received from device')

    def shutdown_event_loop(self):
        self.logger.debug('shutdown_event_loop called')

        try:
            # Hide Cancelled Error exceptions during shutdown
            def shutdown_exception_handler(loop, context):
                if "exception" not in context \
                    or not isinstance(context["exception"],
                                      asyncio.CancelledError):
                    loop.default_exception_handler(context)

            self.loop.set_exception_handler(shutdown_exception_handler)

            # Handle shutdown gracefully by waiting for all tasks
            # to be cancelled
            tasks = asyncio.gather(
                *self.tasks,
                loop=self.loop,
                return_exceptions=True
            )
           
            if self.new_loop:
                tasks.add_done_callback(lambda t: self.loop.stop())
    
            tasks.cancel()

            # Keep the event loop running until it is either
            # destroyed or all tasks have really terminated

            if self.new_loop:
                while (
                    not tasks.done()
                    and not self.loop.is_closed()
                    and not self.loop.is_running()
                ):
                    self.loop.run_forever()
        
        except Exception as ex:
                self.logger.error('Unexpected error in shutdown_event_loop(): %s', format(ex) )

        finally:
            if self.new_loop:

                if (
                    hasattr(self.loop, "shutdown_asyncgens")
                    and not self.loop.is_running()
                ):
                    # Python 3.5
                    self.loop.run_until_complete(
                        self.loop.shutdown_asyncgens()
                    )
                    self.loop.close()
            

    @property
    def device_id(self) -> str:
        """
        Get current device ID (immutable value based on hardware MAC address)

        :return: Device ID.
        :rtype: str
        """
        return self.basic_info['deviceid']

    async def turn_off(self) -> None:
        """
        Turns the device off.
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def is_off(self) -> bool:
        """
        Returns whether device is off.

        :return: True if device is off, False otherwise.
        :rtype: bool
        """
        return not self.is_on

    async def turn_on(self) -> None:
        """
        Turns the device on.
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def is_on(self) -> bool:
        """
        Returns whether the device is on.

        :return: True if the device is on, False otherwise.
        :rtype: bool
        :return:
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    def __repr__(self):
        return "<%s at %s>" % (
            self.__class__.__name__,
            self.host)

    @property
    def available(self) -> bool:

        return self.client.connected_event.is_set()
