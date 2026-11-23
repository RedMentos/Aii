#include "needle.h"
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <vector>
#include <cmath>
#include <iomanip>
std::string readfile(const char* p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("file missing");return {std::istreambuf_iterator<char>(f),{}};}
std::string quote(const std::string& s){std::string o="\"";for(unsigned char c:s){if(c=='"'||c=='\\'){o+='\\';o+=c;}else if(c<32)o+=' ';else o+=c;}return o+'"';}
int main(int argc,char**argv){
 int protocol=dup(STDOUT_FILENO);dup2(STDERR_FILENO,STDOUT_FILENO);FILE* out=fdopen(protocol,"w");
 auto send=[&](const std::string&s){fprintf(out,"%zu\n",s.size());fwrite(s.data(),1,s.size(),out);fflush(out);};
 try{
  if(argc!=3)throw std::runtime_error("usage: worker weights tools");
  setenv("NEEDLE_TELEMETRY","0",1);setenv("DO_NOT_TRACK","1",1);
  std::string weights=readfile(argv[1]),tools=readfile(argv[2]);
  if(needle_load(reinterpret_cast<const unsigned char*>(weights.data()),weights.size())<0)throw std::runtime_error(needle_last_error());
  if(needle_init("locale=de-DE; device=local",tools.c_str(),nullptr)<0)throw std::runtime_error(needle_last_error());
  send("{\"ready\":true}");std::string header;
  while(std::getline(std::cin,header)){
   std::istringstream hs(header);char op;size_t n;if(!(hs>>op>>n)||n>65536)break;
   std::string input(n,'\0');if(!std::cin.read(input.data(),n))break;needle_reset();
   try{
    if(op=='E'){
     int dim=needle_embed(input.c_str(),nullptr,0);if(dim<=0||dim>65536)throw std::runtime_error(needle_last_error());
     std::vector<float> v(dim);if(needle_embed(input.c_str(),v.data(),dim)!=dim)throw std::runtime_error(needle_last_error());
     std::ostringstream s;s<<"{\"embedding\":["<<std::setprecision(9);for(int i=0;i<dim;i++){if(!std::isfinite(v[i]))throw std::runtime_error("nonfinite embedding");if(i)s<<',';s<<v[i];}s<<"]}";send(s.str());
    }else if(op=='C'){
     std::vector<char> b(65536);if(needle_complete(input.c_str(),160,b.data(),b.size())<0)throw std::runtime_error(needle_last_error());send(std::string(b.data()));
    }else throw std::runtime_error("unknown operation");
   }catch(const std::exception&e){send("{\"error\":"+quote(e.what())+"}");}
  }
 }catch(const std::exception&e){send("{\"error\":"+quote(e.what())+"}");return 1;}
 return 0;
}
