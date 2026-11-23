// Deterministic forward-only poll; no gradient exactness or activation authority.
#pragma once
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>
namespace v13_norm_poll {
constexpr double cap = .0010001;
constexpr int max_evaluations = 20;
struct Trial { std::string direction; double radius; int sign; std::vector<float> values; double update_l2; };
inline std::vector<Trial> candidates(const std::vector<float> & original, const std::vector<float> & surrogate) {
    if(original.size()!=1024 || surrogate.size()!=1024)throw std::invalid_argument("Exact1024D master/direction required");
    double squared=0.;for(size_t i=0;i<1024;++i){if(!std::isfinite(original[i])||!std::isfinite(surrogate[i]))throw std::invalid_argument("Finite master/direction required");squared+=double(surrogate[i])*surrogate[i];}
    std::vector<std::pair<std::string,std::vector<double>>> directions;
    if(squared>0.){std::vector<double> direction(1024);for(size_t i=0;i<1024;++i)direction[i]=surrogate[i]/std::sqrt(squared);directions.emplace_back("surrogate_unit_direction_not_exact_gradient",direction);}
    for(int coordinate:{0,341,682,1023}){std::vector<double> direction(1024,0.);direction[coordinate]=1.;directions.emplace_back("coordinate_"+std::to_string(coordinate),direction);}
    std::vector<Trial> result;
    for(const auto & direction:directions)for(double radius:{.001,.0005})for(int sign:{-1,1}){
        auto values=original;double norm=0.;for(size_t i=0;i<1024;++i){values[i]=float(double(original[i])+sign*radius*direction.second[i]);double delta=double(values[i])-original[i];norm+=delta*delta;}
        result.push_back({direction.first,radius,sign,values,std::sqrt(norm)});
    }
    if(result.size()>max_evaluations)throw std::logic_error("Preregistered evaluation budget exceeded");
    return result;
}
inline bool improves(double baseline,double value,double update_l2){
    return std::isfinite(baseline)&&std::isfinite(value)&&std::isfinite(update_l2)&&update_l2>0.&&update_l2<=cap&&value<baseline;
}
}
