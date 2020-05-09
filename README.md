# Intern Project:

Creates a custom CLI command on Juniper MX routers that display chip agnostic counters (see chip_agnostic_command/docs)

### Requirements:
* MX platform  
* Junos>=17.3R1  
* This custom command can only be run on master RE

### Setup:
* Download docker on local device:  
 * https://www.docker.com/products/docker-desktop

* Clone repository onto local Device:  
 * git clone https://css-git.juniper.net/brautio/Intern_Project.

* Configure on router:
 * [edit]   
  root@router-re0# set system scripts language python  

* CD into repository:  
 * cd Intern_Project

* Edit Dockerfile to add login credentials and hostname (credentials must be for root user):  
 * In Dockerfile lines 6-8:  
   ENV host thunder-re0.ultralab.juniper.net <<< Change to your router hostname  
   ENV username root  
   ENV password Juniper <<< Change to your root password  

* Build Docker image:  
 * docker build -t setup_container .  

* Run container:  
 * docker run setup_container:latest  

** Now the commands should be working on router. ** 

Test commands on router:  

* root@router> show center_chip stats | display xml  

and,  

* root@router> show chip-agnostic stats

### Author
Ben Rautio  

### Acknowledgements

Pasvorn Boonmark  
Aditya Mahale  
Devang Patel  
Nitin Kumar  

