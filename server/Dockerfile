FROM eclipse-temurin:17-jdk-alpine
WORKDIR /app
COPY target/*.war app.war
EXPOSE 5000
ENTRYPOINT ["java", "-jar", "app.war"]
