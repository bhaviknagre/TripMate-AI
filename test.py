#from tools.travily_tool import tavily_search
from tools.flight_tool import search_flights

#res = tavily_search("which are the best hotels in INDIA")
#print(res)

res = search_flights("Plan a 7 days India trip from Japan")
print(res)