from .connection import RequestBuilder, Profile
from .utils import DemarchesSimpyException
from .dossier import DossierState, Dossier
from .interfaces import IAction, ILog

#######################
#       ACTIONS       #
# action -> dossier   #
# Pattern:            #
#   - action          #
#   - action          #
# Dossier won't
# implement any action
# on its own
#######################

# TODO: Add an interface action which implement a regular perform action method
# TODO: Annotation : implement general annotation modifier to modify any annotation checkbox, text, etc...

class MessageSender(IAction, ILog):
    r'''
        Class to send message to a dossier
    '''
    def __init__(self, profile : Profile, dossier : Dossier, instructeur_id = None, **kwargs):
        r'''
            Parameters
            ----------
            profile : Profile
                The profile to use to perform the action
            dossier : Dossier
                The dossier to send message to
            instructeur_id : str, optional
                The instructeur id to use to perform the action, if not provided, the profile instructeur id will be used

        '''
        ILog.__init__(self, header="MESSAGE_SENDER", profile=profile, **kwargs)
        IAction.__init__(self, profile, dossier, query_path='./query/send_message.graphql', instructeur_id=instructeur_id)

    def perform(self, mess : str) -> bool:
        r'''
            Send a message to the dossier
            
            Parameters
            ----------
            mess : str
                The message to send

            Returns
            -------
            SUCCESS
                if message was sent
            ERROR
                otherwise

        '''
        variables = {
                "dossierId" : self.dossier.get_id(),
                "instructeurId" : self.instructeur_id,
                "body" : mess
        }
        self.request.add_variable('input',variables)
        try:
            self.request.send_request()
        except DemarchesSimpyException as e:
            self.warning('Message not sent : '+e.message)
            return IAction.ERROR
        self.info('Message sent to '+self.dossier.get_id())
        return IAction.SUCCESS
    
class AnnotationModifier(IAction, ILog):
    '''
        Class to modify anotation of a dossier

        Parameters
        ----------
        profile : Profile
            The profile to use to perform the action
        dossier : Dossier
            The dossier to modify
        instructeur_id : str
            The instructeur id to use to perform the action, if not provided, the profile instructeur id will be used

    '''
    def __init__(self, profile : Profile, dossier : Dossier, instructeur_id = None, **kwargs):
        r'''
            Parameters
            ----------
            profile : Profile
                The profile to use to perform the action
            dossier : Dossier
                The dossier to modify
            instructeur_id : str, optional
                The instructeur id to use to perform the action, if not provided, the profile instructeur id will be used
        '''
        ILog.__init__(self, header="ANOTATION MODIFIER", profile=profile, **kwargs)
        IAction.__init__(self, profile, dossier, instructeur_id=instructeur_id)

        self.input = {
                "dossierId" : self.dossier.get_id(),
                "instructeurId" : self.instructeur_id,
        }

    def perform(self, anotation : dict[str, str], value : str = None) -> int:
        r'''
            Set anotation to the dossier

            Parameters
            ----------
            anotation : dict[str, str]
                The anotation to set, must be a valid anotation structure:

                .. highlight:: python
                .. code-block:: python

                    {
                        "id" : "anotation_id",
                        "stringValue" : "anotation_value"
                    }

                If the anotation is not valid, the method will return False

            value : str
                The value to set to the anotation, if not provided, the anotation will be set to its default value

     

            Returns
            -------
            True 
                if anotation was set
            False
                otherwise
        '''
        #Check if anotation is valid
        if not 'id' in anotation or (not 'stringValue' in anotation and value == None):
            self.error('Invalid anotation provided : '+str(anotation))

        self.input['annotationId'] = anotation['id'] 
        self.input['value'] = anotation['stringValue'] if value == None else value


        self.request.add_variable('input',self.input)

        custom_body = {
            "query": self.request.get_query(),
            "operationName": "dossierModifierAnnotationText",
            "variables": self.request.get_variables()
        }

        try:
            self.request.send_request(custom_body)
        except DemarchesSimpyException as e:
            self.warning('Anotation not set : '+e.message)
            return IAction.ERROR
        self.info('Anotation set to '+self.dossier.get_id())
        return IAction.SUCCESS




class StateModifier(IAction, ILog):
    r'''
        Class to change state of a dossier
    '''

    def __init__(self, profile : Profile, dossier : Dossier, instructeur_id=None, **kwargs):
        r'''
            Parameters
            ----------
            profile : Profile
                The profile to use to perform the action
            dossier : Dossier
                The dossier to change state
            instructeur_id : str, optional
                The instructeur id to use to perform the action, if not provided, the profile instructeur id will be used
        '''
        ILog.__init__(self, header="STATECHANGER", profile=profile, **kwargs)
        IAction.__init__(self, profile, dossier, instructeur_id=instructeur_id)

        if not profile.has_instructeur_id() and instructeur_id == None:
            self.error('No instructeur id was provided to the profile, cannot change state.')
        
        self.input = {
                "dossierId" : self.dossier.get_id(),
                "instructeurId" : self.instructeur_id,
        }


    def perform(self, state: DossierState, msg="") -> int:
        r'''
            Change the state of the dossier

            Parameters
            ----------
            state : DossierState
                The state to set to the dossier
            msg : str, optional
                The message to set to the dossier, if not provided, the message will be set to its default value : ""

        '''

        if state == DossierState.ACCEPTER or state == DossierState.REFUSER or state == DossierState.SANS_SUITE:
            self.input['motivation'] = msg

        self.request.add_variable('input',self.input)
        operation_name = "dossier"
        operation_name += ("Passer" if state == DossierState.INSTRUCTION else "")
        operation_name += ("Repasser" if state == DossierState.CONSTRUCTION else "")
        operation_name += state


        custom_body = {
            "query" : self.request.get_query(),
            "operationName" : operation_name,
            "variables" : self.request.get_variables()
        }
        try:
            self.request.send_request(custom_body)
        except DemarchesSimpyException as e:
            self.warning('State not changed : '+e.message)
            return IAction.ERROR
        self.info('State changed to '+state+' for '+self.dossier.get_id())
        return IAction.SUCCESS