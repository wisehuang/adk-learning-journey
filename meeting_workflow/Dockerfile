# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variables
ENV PYTHONUNBUFFERED 1
ENV GOOGLE_CLOUD_PROJECT "adk-learning-journey"
ENV PORT 8080

# Run streamlit_app.py when the container launches
CMD streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0 