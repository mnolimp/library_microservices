import grpc
from concurrent import futures
import asyncio
import sys
import os

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

import user_pb2
import user_pb2_grpc

from database import get_db_context
from models import User
from sqlalchemy import select


class UserServiceServicer(user_pb2_grpc.UserServiceServicer):

    async def GetUser(self, request, context):
        async with get_db_context() as session:
            result = await session.execute(
                select(User).where(User.id == request.id)
            )

            user = result.scalar_one_or_none()

            if not user:
                return user_pb2.UserResponse()

            return user_pb2.UserResponse(
                id=user.id,
                name=user.full_name,
                email=user.email
            )


async def serve():
    server = grpc.aio.server()

    user_pb2_grpc.add_UserServiceServicer_to_server(
        UserServiceServicer(),
        server
    )

    server.add_insecure_port('0.0.0.0:50052')

    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve())