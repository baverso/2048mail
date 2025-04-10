from typing import Dict, List, Optional, Any
from collections import defaultdict
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket connection manager to handle user connections.
    
    This class manages WebSocket connections by user ID, allowing messages 
    to be sent to specific users rather than broadcasting to everyone.
    """
    
    def __init__(self):
        # Dictionary mapping user IDs to their active WebSocket connections
        self.user_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        # Dictionary mapping WebSocket objects to user IDs for quick lookup
        self.connection_to_user: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accept a new WebSocket connection and associate it with a user ID.
        
        Args:
            websocket: The WebSocket connection to accept
            user_id: The ID of the user making the connection
        """
        # Accept the incoming WebSocket connection
        await websocket.accept()
        # Add the new connection to our dictionary under the user's ID
        self.user_connections[user_id].append(websocket)
        # Store the reverse mapping
        self.connection_to_user[websocket] = user_id
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection when it's closed.
        
        Args:
            websocket: The WebSocket connection that was closed
        """
        # Get the user ID associated with this WebSocket
        user_id = self.connection_to_user.get(websocket)
        if user_id:
            # Remove the WebSocket from the user's connections
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            # Clean up empty user entries
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
            # Remove the reverse mapping
            del self.connection_to_user[websocket]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """
        Send a message to all connections belonging to a specific user.
        
        Args:
            user_id: The ID of the user to send the message to
            message: The message to send
        """
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {str(e)}")
        else:
            logger.warning(f"No active connections for user {user_id}")

    def get_user_id(self, websocket: WebSocket) -> Optional[str]:
        """
        Get the user ID associated with a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to look up
            
        Returns:
            The associated user ID, or None if not found
        """
        return self.connection_to_user.get(websocket)


# Singleton instance of the ConnectionManager
connection_manager = ConnectionManager()