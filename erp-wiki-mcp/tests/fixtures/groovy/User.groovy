package com.example.domain

class User {
    Long id
    String email
    String username
    
    static hasMany = [roles: Role]
    static belongsTo = [Role]
    
    static constraints = {
        email blank: false, unique: true
        username blank: false, unique: true
    }
    
    static mapping = {
        table 'users'
    }
    
    String toString() {
        return "User(${email})"
    }
}
