try:
    from app import app
    import unittest
except Exception as e:
    print("Some Modules are Missing {} ".format(e))

class FlaskTest(unittest.TestCase):

    #Check for the response 200
    def test_index(self):
        tester = app.test_client(self)
        response = tester.get("/")
        statuscode=response.status_code
        self.assertEqual(statuscode,200)

    #check if content return is application/json
    def test_index_content(self):
        tester=app.test_client(self)
        response = tester.get("/metrics")
        self.assertEqual(response.content_type,"text/html; charset=utf-8")


if __name__ == "__main__":
    unittest.main()