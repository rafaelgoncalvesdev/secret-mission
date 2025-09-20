# --- STAGE 1: The Build Stage ---
# Use an official OpenJDK 17 image that includes Maven for building.
# We give this stage a name, "builder", so we can refer to it later.
FROM maven:3.8.5-openjdk-17 AS builder

# Set the working directory inside the container.
WORKDIR /app

# Copy the pom.xml first to leverage Docker's layer caching.
# If the pom.xml doesn't change, Docker won't re-download dependencies.
COPY pom.xml .

# Download all dependencies. This is done in a separate step for caching.
RUN mvn dependency:go-offline

# Copy the rest of the application's source code.
COPY src ./src

# Package the application, skipping the tests.
# This will create the executable .jar file.
RUN mvn package -DskipTests


# --- STAGE 2: The Final Image Stage ---
# Use a slim JRE (Java Runtime Environment) image, which is smaller
# than a full JDK, making our final image more lightweight.
FROM eclipse-temurin:17-jre-jammy

# Set the working directory inside the final container.
WORKDIR /app

# Copy only the built .jar file from the 'builder' stage into our final image.
# We rename it to app.jar for a consistent name.
COPY --from=builder /app/target/*.jar app.jar

# Expose port 8080. This tells Docker that the container listens on this port.
EXPOSE 8080

# The command to run when the container starts.
# This executes our Spring Boot application.
ENTRYPOINT ["java", "-jar", "app.jar"]
