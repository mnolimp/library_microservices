library-microservices/
├── docker-compose.yml
├── .env.example
├── gateway/
│   └── nginx/
│       ├── Dockerfile
│       └── nginx.conf
├── services/
│   ├── catalog-service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   └── db.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── user-service/          (та же структура)
│   ├── lending-service/       (та же структура)
│   └── digital-service/       (та же структура)
├── scripts/
│   ├── seed_data.py
│   └── benchmark_client.py
└── proto/                     
