# XOA RFC Tests Example

This example demonstrates how to run RFC 2544/2889/3918 tests using XOA RFC test framework (xoa-core), and save the result data in csv files.

> Read more about xoa-core and the rfc test suite plugins at https://docs.xenanetworks.com/projects/xoa-core

```run_gui_config.py``` script does the following:

1. Add tester into framework resource inventory and connect to it
2. Convert the GUI config file (```rfc2544.v2544```) into XOA json config file (```rfc2544.json```)
3. Run the test configuration file ```rfc2544.json```
4. Subscribe to result
5. Write final results into csv


```run_xoa_json.py``` script does the following:

1. Add tester into framework resource inventory and connect to it
2. Run the test configuration file ```rfc2544.json```
3. Subscribe to result
4. Write final results into csv