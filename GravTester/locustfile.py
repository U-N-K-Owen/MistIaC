from locust import HttpUser, task, constant

class QuickstartUser(HttpUser):
    wait_time = constant(0.1)

    @task
    def destruction(self):
        self.client.get("/admin")