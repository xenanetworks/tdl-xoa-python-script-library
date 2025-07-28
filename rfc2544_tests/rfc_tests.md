# XOA RFC Tests Example

This example demonstrates how to run RFC 2544/2889/3918 tests using XOA RFC test framework (tdl-xoa-core), and save the result data in csv files.

> Read more about tdl.xoa-core and the rfc test suite plugins at https://docs.xenanetworks.com/projects/tdl-xoa-core

```run_xoa_rfc.py``` script does the following:

1. Add tester into framework resource inventory and connect to it
2. Convert the GUI config file (```demo.x2544``` or ```demo.v2544```) into XOA json config file (```demo.json```)
3. Run the test configuration file ```demo.json```
4. Subscribe to result
5. Write final results into csv

> In the script example, it uses the ```demo.x2544``` file. The only difference between the ```demo.x2544``` and the ```demo.v2544``` file is the file extension name. If you want to run the ```demo.v2544```, simply change line 22 ```XENA2544_CONFIG = PROJECT_PATH / "demo.x2544"``` to ```XENA2544_CONFIG = PROJECT_PATH / "demo.v2544"```
