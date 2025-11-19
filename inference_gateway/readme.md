# Inference Gateway

This folder contains the code for a unified inference gateway

## General design

The is a central gateway program running on the login node, and it will last forever (as long as the program is not been killed or the node is still alive). Every inference request will send to this program from HTTP request (like OpenAI package)

Besides this central gateway, there are several workers that registered under the central gateway. The communication will be done by network, and when the central gateway received an inference request, it will route the request to a specific worker.

## Inference Gateway

