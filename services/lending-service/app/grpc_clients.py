import grpc
import catalog_pb2
import catalog_pb2_grpc
import user_pb2
import user_pb2_grpc


async def get_book(book_id: int):
    async with grpc.aio.insecure_channel(
        'catalog-service:50051'
    ) as channel:
        try:

            stub = catalog_pb2_grpc.CatalogServiceStub(channel)

            response = await stub.GetBook(
                catalog_pb2.BookRequest(id=book_id)
            )

            return {
               'id': response.id,
               'title': response.title,
               'author': response.author,
               'available': response.available
            }
        except Exception as e:
            print("Error on get_book: ", e)



async def get_user(user_id: int):
    async with grpc.aio.insecure_channel(
        'user-service:50052'
    ) as channel:
        try:

            stub = user_pb2_grpc.UserServiceStub(channel)

            response = await stub.GetUser(
                user_pb2.UserRequest(id=user_id)
            )

            return {
               'id': response.id,
                'name': response.name,
                'email': response.email
            }
        except Exception as e:
            print("Error on get_user: ", e)