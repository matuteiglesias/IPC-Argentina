#!/usr/bin/env python3
"""Print the bounded historical monetary-reference finding."""
import json
print(json.dumps({'artifacts':[{'name':f'EPHARG_annual_input_{y}.csv','classification':'unresolved','evidence':'not present in this repository or workspace'} for y in (22,23,24,25)],'identifier':'provisional:legacy-price-series-unidentified','replacement_permitted':False},indent=2))
