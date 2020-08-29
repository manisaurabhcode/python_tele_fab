from flask import Flask,jsonify,request,abort,json

app = Flask(__name__)
 
sample_mock_response = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

@app.route('/')
def hello_world():
   return 'Hello World'

@app.route('/sc1')
def create_file():
   return 'Hello World'

@app.route('/todo/api/v1.0/mock', methods=['GET'])
def get_tasks():
    return jsonify({'sample_mock_response': sample_mock_response})

@app.route('/sn/gesw/sc1', methods=['POST'])
def create_task():
    if not request.json:
        abort(400)
    print(request.json)
    f = open("./incoming/myfile.txt", "w")
    f.write(json.dumps(request.json))
    f.close
    return jsonify({'task': 'task'}), 201

if __name__ == '__main__':
   app.run()