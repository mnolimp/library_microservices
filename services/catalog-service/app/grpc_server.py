import grpc
from concurrent import futures
import asyncio
import sys
import os

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

import catalog_pb2
import catalog_pb2_grpc

from database import get_db
from models import Book
from sqlalchemy import select


class CatalogServiceServicer(catalog_pb2_grpc.CatalogServiceServicer):

    async def GetBook(self, request, context):
        async with get_db() as session:
            result = await session.execute(
                select(Book).where(Book.id == request.id)
            )

            book = result.scalar_one_or_none()

            if not book:
                return catalog_pb2.BookResponse()

            return catalog_pb2.BookResponse(
                id=book.id,
                title=book.title,
                author=book.author
            )


async def serve():
    server = grpc.aio.server()

    catalog_pb2_grpc.add_CatalogServiceServicer_to_server(
        CatalogServiceServicer(),
        server
    )

    server.add_insecure_port('0.0.0.0:50051')

    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve())