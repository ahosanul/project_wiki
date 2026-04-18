package com.example

class UserController {
    
    UserService userService
    
    def index() {
        redirect action: 'list'
    }
    
    def list() {
        [users: User.list(params)]
    }
    
    def show() {
        def user = userService.findById(params.id as Long)
        if (!user) {
            flash.message = 'User not found'
            redirect action: 'list'
            return
        }
        [user: user]
    }
    
    def save() {
        def user = new User(params)
        if (user.save()) {
            flash.message = 'User saved successfully'
            redirect action: 'show', id: user.id
        } else {
            render view: 'create', model: [user: user]
        }
    }
    
    def delete() {
        def user = User.get(params.id as Long)
        if (user) {
            user.delete()
            flash.message = 'User deleted'
        }
        redirect action: 'list'
    }
}
