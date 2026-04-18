// Sample Java file for extractor testing
package com.example.service;

import org.springframework.stereotype.Service;
import com.example.domain.User;

@Service
public class UserService {
    
    /**
     * Finds a user by their ID.
     * @param userId the user ID
     * @return the user or null if not found
     */
    public User findById(Long userId) {
        if (userId == null) {
            return null;
        }
        return new User(userId, "test@example.com");
    }
    
    public void saveUser(User user) {
        if (user != null) {
            System.out.println("Saving user: " + user.getEmail());
        }
    }
    
    private String formatEmail(String email) {
        return email.toLowerCase();
    }
}
