*** Settings ***
Documentation   This is a test
Library    XOARobot.py

*** Variables ***
${CHASSIS}      10.165.136.66
${PORT}         8/0

*** Keywords ***
Read Port Description
    [Documentation]    This performs a read
    [Arguments]            ${port}=${PORT}
    ${value}=    Get Port Description    ${port}
    RETURN    ${value}

*** Test Cases ***
Just to Try
    [Documentation]    This is just a test
    Log    this is just a message
    Connect Chassis    ${CHASSIS}
    Reserve Port       ${PORT}
    Reset Port    ${PORT}
    Release Port    ${PORT}
    ${x}=   Read Port Description
    Log To Console    ${x}
    Disconnect Chassis
    