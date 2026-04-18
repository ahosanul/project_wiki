#!/usr/bin/env groovy
// @Grab('org.codehaus.groovy:groovy:3.0.19')
// Groovy AST Server - reads file paths from stdin, outputs JSON AST to stdout

import groovy.json.JsonOutput
import groovy.util.ConfigSlurper

class AstServer {
    static void main(String[] args) {
        System.in.eachLine { line ->
            if (!line || line.trim().isEmpty()) {
                return
            }
            
            def filePath = line.trim()
            def result = [:]
            
            try {
                def file = new File(filePath)
                if (!file.exists()) {
                    result = [
                        file: filePath,
                        status: 'failed',
                        error: "File not found: ${filePath}"
                    ]
                } else {
                    def content = file.text
                    def artifactType = System.getenv('ARTIFACT_TYPE') ?: 'plain_groovy'
                    
                    if (artifactType == 'grails_config' || filePath.endsWith('.groovy') && 
                        (filePath.contains('/conf/') || filePath.contains('\\conf\\'))) {
                        // Use ConfigSlurper for config files
                        try {
                            def config = new ConfigSlurper().parseText(content)
                            def flatConfig = flattenConfig(config)
                            result = [
                                file: filePath,
                                status: 'ok',
                                type: 'config',
                                ast: flatConfig
                            ]
                        } catch (Exception e) {
                            // Fall back to normal AST parsing
                            def ast = parseGroovyAst(content)
                            result = [
                                file: filePath,
                                status: 'ok',
                                type: 'ast',
                                ast: ast
                            ]
                        }
                    } else {
                        // Normal Groovy AST parsing
                        def ast = parseGroovyAst(content)
                        result = [
                            file: filePath,
                            status: 'ok',
                            type: 'ast',
                            ast: ast
                        ]
                    }
                }
            } catch (Exception e) {
                result = [
                    file: filePath,
                    status: 'failed',
                    error: e.message,
                    stackTrace: e.stackTrace.collect { it.toString() }.take(5)
                ]
            }
            
            println JsonOutput.toJson(result)
            System.out.flush()
        }
    }
    
    static def parseGroovyAst(String source) {
        def shell = new GroovyShell()
        def unit = shell.getClassLoader()
        
        try {
            // Use CompilationUnit with CONVERSION phase
            def compilerConfiguration = new org.codehaus.groovy.control.CompilerConfiguration()
            compilerConfiguration.setTargetDirectory(new File(System.getProperty('java.io.tmpdir')))
            
            def compilationUnit = new org.codehaus.groovy.control.CompilationUnit(compilerConfiguration)
            compilationUnit.addSource("script.groovy", source)
            compilationUnit.compile(org.codehaus.groovy.control.CompilePhase.CONVERSION)
            
            def ast = []
            compilationUnit.astClasses.each { clazz ->
                ast << classNodeToMap(clazz)
            }
            
            return [
                classes: ast,
                scripts: compilationUnit.scriptClass ? [classNodeToMap(compilationUnit.scriptClass)] : []
            ]
        } catch (Exception e) {
            // Fallback: basic source analysis
            return [
                error: "Full AST parsing failed: ${e.message}",
                fallback: true,
                lines: source.split('\n').size()
            ]
        }
    }
    
    static def classNodeToMap(ClassNode clazz) {
        def result = [
            name: clazz.name?.split('\\.')?.last() ?: clazz.name,
            fqn: clazz.name,
            superClass: clazz.superClass?.name,
            interfaces: clazz.interfaces?.collect { it.name } ?: [],
            annotations: clazz.annotations?.collect { annToMap(it) } ?: [],
            fields: [],
            methods: []
        ]
        
        clazz.fields?.each { field ->
            result.fields << [
                name: field.name,
                type: field.type?.name,
                line: field.lineNumber ?: 0,
                annotations: field.annotations?.collect { annToMap(it) } ?: [],
                isStatic: field.isStatic(),
                isFinal: field.isFinal()
            ]
        }
        
        clazz.methods?.each { method ->
            result.methods << [
                name: method.name,
                returnType: method.returnType?.name,
                params: method.parameters?.collect { [name: it.name, type: it.type?.name] } ?: [],
                line: method.lineNumber ?: 0,
                endLine: (method.lineNumber ?: 0) + 10, // Approximate
                isStatic: method.isStatic(),
                isAbstract: method.isAbstract(),
                annotations: method.annotations?.collect { annToMap(it) } ?: []
            ]
        }
        
        return result
    }
    
    static def annToMap(AnnotationNode ann) {
        [
            name: ann.classNode?.name ?: ann.name,
            members: ann.members?.collectEntries { k, v -> [(k.text): v.text] } ?: [:]
        ]
    }
    
    static def flattenConfig(config, prefix = '') {
        def result = [:]
        config.each { key, value ->
            def fullKey = prefix ? "${prefix}.${key}" : key
            if (value instanceof Map) {
                result.putAll(flattenConfig(value, fullKey))
            } else {
                result[fullKey] = value
            }
        }
        return result
    }
}
