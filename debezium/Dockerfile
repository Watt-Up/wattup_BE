FROM quay.io/debezium/connect:2.5

# 1. MongoDB 커넥터 전용 격리 폴더 생성
RUN mkdir -p /kafka/connect/mongo-sink

# 2. postgres 폴더가 아닌, 방금 만든 전용 폴더에 다운로드 (충돌 방지)
RUN curl https://repo1.maven.org/maven2/org/mongodb/kafka/mongo-kafka-connect/1.11.0/mongo-kafka-connect-1.11.0-all.jar \
    -o /kafka/connect/mongo-sink/mongo-kafka-connect-1.11.0-all.jar

# MongoDB 싱크 커넥터 라이브러리 다운로드 및 설치
#RUN curl https://repo1.maven.org/maven2/org/mongodb/kafka/mongo-kafka-connect/1.11.0/mongo-kafka-connect-1.11.0-all.jar \
#    -o /kafka/connect/debezium-connector-postgres/mongo-kafka-connect-1.11.0-all.jar
