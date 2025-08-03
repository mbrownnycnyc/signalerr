
import subprocess
import json
import logging
import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
import os
import signal

logger = logging.getLogger(__name__)

class SignalMessage:
    def __init__(self, data: Dict):
        self.raw_data = data
        self.envelope = data.get('envelope', {})
        self.source = self.envelope.get('source', '')
        self.source_number = self.envelope.get('sourceNumber', '')
        self.timestamp = self.envelope.get('timestamp', 0)
        
        # Message content
        data_message = self.envelope.get('dataMessage', {})
        self.message = data_message.get('message', '')
        self.group_info = data_message.get('groupInfo')
        self.attachments = data_message.get('attachments', [])
        
        # Group information
        self.is_group_message = self.group_info is not None
        self.group_id = self.group_info.get('groupId') if self.group_info else None
        
    def is_from_user(self, phone_number: str) -> bool:
        """Check if message is from specific user"""
        return self.source_number == phone_number or self.source == phone_number
    
    def get_sender(self) -> str:
        """Get sender phone number"""
        return self.source_number or self.source
    
    def get_text(self) -> str:
        """Get message text"""
        return self.message.strip()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'sender': self.get_sender(),
            'message': self.get_text(),
            'timestamp': self.timestamp,
            'is_group': self.is_group_message,
            'group_id': self.group_id
        }

class SignalClient:
    def __init__(self, phone_number: str, signal_cli_path: str = '/usr/local/bin/signal-cli', config_dir: str = None):
        self.phone_number = phone_number
        self.signal_cli_path = signal_cli_path
        self.config_dir = config_dir or f"/home/signal/.local/share/signal-cli"
        self.message_handlers = []
        self.is_running = False
        self.daemon_process = None
        self.receive_thread = None
        
    def add_message_handler(self, handler: Callable[[SignalMessage], None]):
        """Add a message handler function"""
        self.message_handlers.append(handler)
    
    def _run_signal_command(self, args: List[str], input_data: str = None) -> subprocess.CompletedProcess:
        """Run signal-cli command"""
        cmd = [
            self.signal_cli_path,
            '-a', self.phone_number,
            '--config', self.config_dir
        ] + args
        
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Signal command failed: {' '.join(cmd)}")
                logger.error(f"Error output: {result.stderr}")
            
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Signal command timed out: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Failed to run signal command: {e}")
            raise
    
    def send_message(self, recipient: str, message: str, group_id: str = None) -> bool:
        """Send a message to a recipient or group"""
        try:
            args = ['send', '-m', message]
            
            if group_id:
                args.extend(['-g', group_id])
            else:
                args.append(recipient)
            
            result = self._run_signal_command(args)
            
            if result.returncode == 0:
                logger.info(f"Message sent to {recipient or group_id}")
                return True
            else:
                logger.error(f"Failed to send message: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_message_to_group(self, group_id: str, message: str) -> bool:
        """Send message to a group"""
        return self.send_message(None, message, group_id)
    
    def create_group(self, name: str, members: List[str]) -> Optional[str]:
        """Create a new group"""
        try:
            args = ['updateGroup', '-n', name] + members
            result = self._run_signal_command(args)
            
            if result.returncode == 0:
                # Parse group ID from output
                output = result.stdout.strip()
                # Group ID is typically in the output, but format may vary
                logger.info(f"Group created: {name}")
                return output  # This might need parsing depending on signal-cli output
            else:
                logger.error(f"Failed to create group: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return None
    
    def list_groups(self) -> List[Dict]:
        """List all groups"""
        try:
            result = self._run_signal_command(['listGroups'])
            
            if result.returncode == 0:
                # Parse groups from output
                groups = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Parse group information (format may vary)
                        groups.append({'raw': line})
                return groups
            else:
                logger.error(f"Failed to list groups: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing groups: {e}")
            return []
    
    def receive_messages(self) -> List[SignalMessage]:
        """Receive pending messages"""
        try:
            result = self._run_signal_command(['receive', '--json'])
            
            if result.returncode == 0 and result.stdout.strip():
                messages = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            message = SignalMessage(data)
                            messages.append(message)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse message JSON: {e}")
                            continue
                
                return messages
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            return []
    
    def start_daemon(self) -> bool:
        """Start signal-cli in daemon mode for real-time message receiving"""
        try:
            cmd = [
                self.signal_cli_path,
                '-a', self.phone_number,
                '--config', self.config_dir,
                'daemon',
                '--json'
            ]
            
            self.daemon_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            logger.info("Signal daemon started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start signal daemon: {e}")
            return False
    
    def stop_daemon(self):
        """Stop the signal daemon"""
        if self.daemon_process:
            try:
                self.daemon_process.terminate()
                self.daemon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()
                self.daemon_process.wait()
            
            self.daemon_process = None
            logger.info("Signal daemon stopped")
    
    def _message_receiver_thread(self):
        """Thread function to receive messages from daemon"""
        while self.is_running and self.daemon_process:
            try:
                if self.daemon_process.poll() is not None:
                    logger.error("Signal daemon process died")
                    break
                
                line = self.daemon_process.stdout.readline()
                if line:
                    try:
                        data = json.loads(line.strip())
                        message = SignalMessage(data)
                        
                        # Call all message handlers
                        for handler in self.message_handlers:
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"Message handler error: {e}")
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse daemon message: {e}")
                        continue
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in message receiver thread: {e}")
                break
    
    def start_listening(self) -> bool:
        """Start listening for messages"""
        if self.is_running:
            logger.warning("Already listening for messages")
            return True
        
        if not self.start_daemon():
            return False
        
        self.is_running = True
        self.receive_thread = threading.Thread(target=self._message_receiver_thread, daemon=True)
        self.receive_thread.start()
        
        logger.info("Started listening for messages")
        return True
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.is_running = False
        
        if self.receive_thread:
            self.receive_thread.join(timeout=5)
        
        self.stop_daemon()
        logger.info("Stopped listening for messages")
    
    def is_registered(self) -> bool:
        """Check if the phone number is registered with Signal"""
        try:
            # Try to list contacts to verify registration
            result = self._run_signal_command(['listContacts'])
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking registration: {e}")
            return False
    
    def register(self, captcha_token: str = None) -> bool:
        """Register phone number with Signal"""
        try:
            args = ['register']
            if captcha_token:
                args.extend(['--captcha', captcha_token])
            
            result = self._run_signal_command(args)
            
            if result.returncode == 0:
                logger.info(f"Registration initiated for {self.phone_number}")
                return True
            else:
                logger.error(f"Registration failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            return False
    
    def verify(self, verification_code: str, pin: str = None) -> bool:
        """Verify phone number with code"""
        try:
            args = ['verify', verification_code]
            if pin:
                args.extend(['--pin', pin])
            
            result = self._run_signal_command(args)
            
            if result.returncode == 0:
                logger.info(f"Verification successful for {self.phone_number}")
                return True
            else:
                logger.error(f"Verification failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error during verification: {e}")
            return False
