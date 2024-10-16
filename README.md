# autogen-arxiv-summary

## Introduction

This is an example to use Microsoft AutoGen library to retrieve a number of latest papers in a specific topic from Arxiv (well, any place as long as there is an API can be called) and summarize them with LLM and return as a XML. 

Once the flask app started, you can POST the request with the sample json body, and the response is a XML in which no more the given number of papers' summary are included.
