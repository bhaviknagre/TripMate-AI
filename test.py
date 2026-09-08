#from tools.travily_tool import tavily_search
#from tools.flight_tool import search_flights
from backend import run_travel_agent

#res = tavily_search("which are the best hotels in INDIA")
#res = search_flights("Plan a 7 days India trip from Japan")

user_input = input("enter the travel request:")
response = run_travel_agent(
    user_input=user_input,
    thread_id="test_user"
)
print("\nFInal respose:\n")
print(response["answer"])