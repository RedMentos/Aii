import time
from .common import uid,now,dumps
FIELDS={
 "OutputPolicyDecision":{"rule_id":str,"rule_version":str,"query_ref":dict,"answer_ref":dict,"output_authority":str,"model_generated":bool},
 "ExecutiveControlContext":{"session_id":str,"query_ref":dict,"state_version":int,"allowed_routes":list,"external_action_authority":bool,"resource_state":str,"compact_view":dict,"probe_only":bool},
 "OutputSnapshot":{"session_id":str,"query_ref":dict,"memory_refs":list,"status":str,"authority":str,"model_generated":bool,"semantic_answer_available":bool},
 "PlasticityState":{"component":str,"update_id":str,"trials":int,"plasticity_gain":(int,float),"stability_score":(int,float),"retention_pass":bool,"saturation":(int,float,type(None)),"consolidation_ready":bool,"semantic_truth_authority":bool},
 "PlasticityBudget":{"component":str,"update_id":str,"policy":dict,"native_parameter_authority":int},
 "MemoryRetrievalDecision":{"query_ref":dict,"memory_ref":dict,"key_ref":dict,"memory_id":str,"context_revision":str,"prediction":(dict,type(None)),"semantic_truth_authority":bool,"fallback_reason":str},
 "ControlCalibration":{"source_ref":dict,"native_control":dict,"model_revision":str,"context_revision":str,"prediction":(dict,type(None)),"semantic_truth_authority":bool},
 "OutputAdapterContext":{"context_ref":dict,"model_revision":str,"context_revision":str,"native_role":str},
 "OutputAdapterDecision":{"context_ref":dict,"model_revision":str,"context_revision":str,"prediction":(dict,type(None)),"semantic_truth_authority":bool,"fallback_reason":str},
 "WorldTransition":{"action_id":str,"source_ref":dict,"outcome_source_ref":dict,"action_role":str,"corollary_packet_id":str,"teacher_truth_authority":bool},
 "StudentEvaluation":{"percept_packet_id":str,"source_ref":dict,"student_route":str,"teacher_route":str,"agreement":bool,"routing_authority":int},
 "LatentTapPacket":{"role":str,"source_ref":dict,"tap_id":str,"model_revision":str,"token_ids":list,"feature_path":str,"feature_sha256":str,"shape":list},
 "ExecutiveDecision":{"component":str,"context_ref":dict,"baseline":str,"action":str,"learned":bool,"context_revision":str,"trajectory_offer_ids":list},
 "ActionPrediction":{"action_type":str,"profile_id":str,"prediction":dict},
 "PredictionOutcome":{"action_id":str,"observation":dict},
 "EventEnvelope":{"source_ref":dict,"authority":str,"kind":str},
 "SourceRef":{"source_id":str,"sha256":str,"char_start":int,"char_end":int,"modality":str},
 "PerceptPacket":{"source_ref":dict,"segments":list,"modality":str},
 "OfferPacket":{"role":str,"based_on_state_version":int,"deadline_monotonic_ns":int,"evidence_refs":list,"offer":dict,"confidence":(int,float)},
 "QueryPacket":{"target_role":str,"goal":str,"source_refs":list},
 "MessagePacket":{"channel":str,"sender":str,"receiver":str,"source_refs":list,"content":dict},
 "WorkspaceSlot":{"owner":str,"source_refs":list,"content":dict},
 "ExecState":{"session_id":str,"state_version":int,"goal":str,"constraints":list,"last_event_id":str},
 "JEFBroadcastPacket":{"state_version":int,"goal":str,"constraints":list,"source_refs":list},
 "ActionIntent":{"action_id":str,"action_type":str,"permission":str},
 "CorollaryCopy":{"action_id":str,"expected":dict,"self_caused":bool},
 "ActionOutcome":{"action_id":str,"status":str,"actual":dict},
 "HumanDecision":{"kind":str,"value":str,"source_ref":dict,"learning_permission":str},
 "ExperienceRecord":{"source_ref":dict,"self_candidate_hash":str,"outcome":str},
 "MemoryRecord":{"memory_id":str,"kind":str,"source_ref":dict,"scope":str,"key":str},
 "LearningTrace":{"path_id":str,"activity":(int,float),"eligibility":(int,float),"authority":str},
 "ModulatorPacket":{"epistemic_evidence":(int,float),"human_correction":(int,float),"task_success":(int,float),"resource_cost":(int,float),"safety_veto":bool},
 "UpdateManifest":{"update_id":str,"base_brain_generation_id":str,"status":str,"artifact_hash":str,"metrics":dict},
 "CheckpointManifest":{"checkpoint_id":str,"hashes":dict},
 "BrainGenerationManifest":{"parent_generation_id":(str,type(None)),"rule_version":str,"hashes":dict,"config":dict,"models":dict},
 "ModelManifest":{"role":str,"model_id":str,"exact_revision":str,"file_hashes":dict,"runner_id":str},
 "CapabilityProfile":{"capability_id":str,"current_mode":str,"reason":str},
 "PathSpec":{"path_id":str,"mode":str,"read_gain":(int,float),"learn_gain":(int,float)},
 "KnobSpec":{"id":str,"kind":str,"value":(int,float,bool),"owner":str},
 "ReplayItem":{"replay_type":str,"source_refs":list,"priority":(int,float),"max_authority":str},
 "FocalItem":{"item_id":str,"source_kind":str,"source_refs":list,"fact_hypothesis_status":str,"state_type":str,"salience":(int,float),"uncertainty":(int,float),"priority":(int,float)},
 "TrainRunnerProof":{"trainable_parameter_count":int,"runner_revision":str,"device":dict,"checks":dict},
 "ReceiverCalibration":{"sender_revision":str,"receiver_revision":str,"injection_level":int,"metrics":dict}}
# WP-N1/N2/N4 (focal.py): C4 loop rounds, Inquisition P1/P2 steps, C5 candidate selection.
FIELDS["FocalCycle"]={"cycle":int,"decision":str,"coalition":list,"signals":dict,"budget":dict}
FIELDS["InquisitionStep"]={"mode":str,"speaker":str,"target_item_id":str,"verdict":str,"evidence":dict}
FIELDS["ActionSelection"]={"selected":dict,"candidates":list,"suppressed":list,"permission_class":str}
FIELDS["EffortDecision"]={"mode":str,"effort":(int,float),"wake":str,"wake_source":str,"plan":dict,"signals":dict,"constraints":list}
FIELDS["AttentionRequest"]={"requester":str,"target":str,"reason":str,"priority":(int,float),"budget":int,"resolution":str}  # WP-N5 §4B.2
FIELDS["ContextPlan"]={"mode":str,"layout":str,"applied":bool,"budget":dict,"items":list,"cache":dict,"exact":dict,"decisions":list}  # WP-N7 §8.3-8.5
FIELDS["SelfCorollary"]={"action_id":str,"issued_at":(int,float),"intended_effect":str,"predicted_observations":list,"uncertainty":(int,float),"causal_hypothesis":str,"expected_cost":dict,"permission_snapshot":dict}  # WP-N9 §85.7
FIELDS["SelfWorldAttribution"]={"channel":str,"attribution":str,"reason":str,"action_ids":list}  # WP-N9 §7.5
FIELDS["JEFBroadcastCache"]={"state_version":int,"cache":dict,"broadcast_packet_id":str,"size_bytes":int}  # WP-N3 §3.4.2
FIELDS["JEFBridgeTurn"]={"scaffold_decision":str,"learned_decision":str,"observer_mode":str,"offers":list,"query_proposal":dict}  # WP-N3
FIELDS["ReflexEvent"]={"reflex":str,"action":str,"detail":dict}  # WP-F §5.3
FIELDS["EgressCheck"]={"action_type":str,"ok":bool,"violations":list,"rewrites":int}  # WP-N4 C6
FIELDS["ToolProposal"]={"tool":str,"args":dict,"policy_status":str,"truth_authority":int}  # WP-K/AG10 C2 tool proposal for C5
FIELDS["C2ExecutivePacket"]={"route":str,"fields":dict,"truth_authority":int}  # WP-T1 structured C2 output (tool, memory key, answer type)
FIELDS["OutputBrokerDecision"]={"authority":str,"egress_type":str,"status":str,"overridden":list,"conflicts":list,"committed":bool,"late":list,"rewrites":int}  # WP-T7 C7 output broker
FIELDS["AttentionResponse"]={"request_packet_id":str,"status":str,"granted_budget":int,"truth_authority":int}  # WP-N5 §4B.3
BASE={"schema_version":str,"packet_id":str,"producer_component":str,"producer_version":str,"event_id":str,"created_monotonic_ns":int,"created_wall_time":(int,float),"brain_generation_id":str,"provenance":list}
def validate(kind,obj):
    if kind not in FIELDS:raise ValueError("Unbekanntes Schema")
    for k,t in (BASE|FIELDS[kind]).items():
        if k not in obj or not isinstance(obj[k],t):raise ValueError(f"{kind}.{k}: fehlt/falscher Typ")
    if obj["schema_version"]!="1.0":raise ValueError("Schema-Version inkompatibel")
    dumps(obj)
    if kind=="OutputPolicyDecision" and (obj['output_authority']!='APPROVED_FIXED_RULE' or obj['model_generated']):raise ValueError('Fixed output policy source-only authority')
    if kind=="OutputSnapshot" and (obj['authority']!='SOURCE_SYSTEM_REPORT' or obj['model_generated'] or obj['semantic_answer_available']):raise ValueError('Snapshot source-only authority')
    if kind=="ExecutiveControlContext" and (obj['external_action_authority'] or obj['allowed_routes']!=['simple','detail','gist','both']):raise ValueError('Control local processing permissions')
    if kind=="ExecState":
        optional={'goal_source_ref':(dict,type(None)),'goal_sequence':list,'active_task':(dict,type(None)),'current_action_intent':(dict,type(None)),'salient_A_offer':(dict,type(None)),'salient_B_offer':list,'memory_refs':list,'uncertainty':dict,'resource_state':dict,'permission_flags':dict,'open_questions':list,'conversation_event_version':int}
        for name,types in optional.items():
            if name in obj and not isinstance(obj[name],types):raise ValueError('ExecState.'+name+': falscher Typ')
    if kind=="SourceRef" and not 0<=obj["char_start"]<=obj["char_end"]:raise ValueError("SourceRef-Bereich")
    if kind=="OfferPacket" and (obj["role"] not in {"B1_DETAIL","B2_GIST"} or not 0<=obj["confidence"]<=1):raise ValueError("Offer role/confidence")
    if kind=="MessagePacket" and obj["channel"] not in {"NO_MESSAGE","SOURCE_EXACT","CONTROL","SYMBOLIC"}:raise ValueError("B3 latent authority=0")
    if kind=="EffortDecision" and (obj["wake"] not in {"none","detail","gist","both"} or not 0<=obj["effort"]<=1):raise ValueError("Effort wake/range")
    if kind=="ModulatorPacket":
        ch=obj.get('channels',{})
        if not isinstance(ch,dict) or not all(isinstance(k,str) and isinstance(v,(int,float)) and not isinstance(v,bool) and -1<=v<=1 for k,v in ch.items()):raise ValueError("Modulator channels [-1,1]")
        if obj.get('finality','FINAL') not in {"PROVISIONAL","FINAL"}:raise ValueError("Modulator finality")
    if kind=="AttentionRequest" and (obj["target"] not in {"A_SOURCE","B1","B2","MEMORY","WORLD","TOOL","SELF"} or obj["reason"] not in {"novelty","conflict","exactness","goal","verify","recall"} or not 0<=obj["priority"]<=1 or obj["budget"]<1):raise ValueError("Attention request target/reason/priority/budget")
    if kind=="AttentionResponse" and (obj["status"] not in {"GRANTED","NOT_AVAILABLE","TOO_EXPENSIVE"} or obj["truth_authority"]!=0):raise ValueError("Attention response status/authority (gain != truth)")
    if kind=="OutputBrokerDecision" and (obj["rewrites"]!=0 or obj["authority"] not in {"APPROVED_FIXED_RULE","EXPLICIT_EXACT_COPY","MODEL_ANSWER","SOURCE_SYSTEM_REPORT","NONE"}):raise ValueError("Broker never rewrites; known authority only")
    if kind=="SelfWorldAttribution" and obj["attribution"] not in {"SELF","EXTERNAL","MIXED","UNCLEAR"}:raise ValueError("Self/World attribution class")
    if kind=="LearningTrace" and not 0<=obj["activity"]<=1:raise ValueError("Trace activity [0,1]")
    if kind=="FocalItem" and (obj["state_type"] not in {"ACTIVE","REACTIVATABLE","EPISODIC_POINTER"} or (obj["source_kind"] in {"B1_DETAIL","B2_GIST"} and obj["fact_hypothesis_status"]=="FACT")):raise ValueError("FocalItem state/authority")
    if kind=="InquisitionStep" and (obj["speaker"] not in {"P1","P2"} or obj.get("fact_authority")):raise ValueError("Inquisition scaffold authority")
    if kind=="FocalCycle" and obj["decision"] not in {"IGNORE","INCORPORATE_A","INCORPORATE_B","INCORPORATE_AB","QUERY_A","QUERY_B","QUERY_AB"}:raise ValueError("FocalCycle decision")
    if kind=="EventEnvelope" and obj["authority"] not in {"AUTHORITATIVE","PROVISIONAL"}:raise ValueError("Authority")
    return obj
def packet(schema,producer,event,generation,provenance=None,**payload):
    return validate(schema,dict(schema_version="1.0",packet_id=uid("pkt"),producer_component=producer,producer_version="0.1.0",event_id=event,created_monotonic_ns=time.monotonic_ns(),created_wall_time=now(),brain_generation_id=generation,provenance=provenance or [],**payload))
def offer_is_fresh(p,event,generation,version,output_committed=False):
    validate("OfferPacket",p)
    return not output_committed and p["event_id"]==event and p["brain_generation_id"]==generation and p["based_on_state_version"]==version and p["deadline_monotonic_ns"]>=time.monotonic_ns()
