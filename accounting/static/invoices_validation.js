$(document).ready(function(){

    ko.validation.init({

        registerExtenders: true,
        messagesOnModified: true,
        insertMessages: true,
        parseInputAttributes: true,
        errorClass:'errorStyle',
        messageTemplate: null

    }, true);

    var viewModel ={

        policy_number: ko.observable().extend({ required: true, minLength: 1, maxLength:128}),
        effective_date: ko.observable().extend({ required: true}),

        submit : function(){
            $('div.alert-success').hide();
            $('div.alert-danger').hide();
            if(viewModel.errors().length === 0){
                $('div.alert-success').show();
                return true
            }else{
                $('div.alert-danger').show();
            }
        }
    };

   //Catch errors
    viewModel.errors = ko.validation.group(viewModel);
    ko.applyBindings(viewModel);

});