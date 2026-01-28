# Security Considerations

This document outlines the security measures and considerations implemented in
toolbelt to protect against accidental exposure of sensitive data.

## Environment Variable Filtering

Toolbelt implements strict filtering of environment variables to prevent
accidental exposure of sensitive information such as API tokens, passwords, and
internal service URLs.

### Why Filter Environment Variables?

Environment variables are commonly used to store sensitive configuration data:

- API tokens and access keys (`GITHUB_TOKEN`, `AWS_ACCESS_KEY_ID`)
- Database connection strings (`DATABASE_URL`)
- Authentication credentials (`SLACK_TOKEN`, `DISCORD_WEBHOOK_URL`)
- Internal service endpoints with embedded credentials
- Personal access tokens and secrets

Without filtering, these sensitive values could be:

- **Logged** in debug output or error messages
- **Displayed** in configuration listings (`toolbelt config --show-variables`)
- **Passed to external tools** as command arguments
- **Included in shared configuration files** for troubleshooting

### Prefix-Based Access Control

Toolbelt only allows environment variables with specific prefixes to be used in
runtime template expansion and overrides:

**Allowed Prefixes:**

- `TOOLBELT_*` - Toolbelt-specific variables
- `TB_*` - Short form of toolbelt variables
- `TBELT_*` - Alternative spelling
- `CI_*` - Common CI/CD system variables (e.g., `CI_COMMIT_SHA`,
  `CI_BUILD_NUMBER`)
- `BUILD_*` - Build system variables

**Examples of Allowed Variables:**

```bash
TOOLBELT_PROJECT_ROOT=/path/to/project
TB_VERSION=1.2.3
CI_BRANCH=main
BUILD_NUMBER=42
```

**Examples of Blocked Variables:**

```bash
GITHUB_TOKEN=secret123          # No approved prefix
AWS_ACCESS_KEY_ID=key123        # No approved prefix
DATABASE_URL=postgres://...     # No approved prefix
SLACK_WEBHOOK=https://...       # No approved prefix
```

### Security Benefits

1. **Defense in Depth**: Prevents accidental inclusion of sensitive environment
   variables
2. **Principle of Least Privilege**: Only explicitly approved variables are
   accessible
3. **Auditability**: Clear distinction between approved and unapproved variables
4. **Conflict Prevention**: Avoids naming conflicts with other tools'
   environment variables
5. **User Awareness**: Requires explicit opt-in for variable usage

### Config-Time Variable Expansion

While runtime template expansion is restricted to prefixed variables,
**configuration loading** allows referencing any environment variable in the
`variables` section of config files:

```yaml
variables:
  TB_PROJECT_SOURCE: '${HOME}/project' # References any env var
  TB_CONFIG_PATH: '${XDG_CONFIG_HOME}/toolbelt' # References any env var
  TB_VERSION: '1.0.0' # Static value
```

This provides flexibility for configuration while maintaining security:

- Values are captured at config load time and become static strings
- Sensitive values are "baked in" during configuration loading
- Runtime template expansion still uses only filtered variables
- The `--show-variables` command reveals which variables used external
  references

### Runtime Behavior

At runtime, only filtered environment variables can:

- Override configuration values
- Be used in tool command templates
- Appear in `--show-variables` output

This ensures that sensitive data cannot be accidentally exposed during tool
execution or debugging.

### Configuration Visibility and Debugging

Toolbelt provides comprehensive visibility into how variables are defined and
resolved:

**`--show-variables` Command:**

```bash
tb config --show-variables
```

This command displays:

- **Variable names** and their **final resolved values**
- **Raw template definitions** for variables defined with templates in config
  files
- **Source indicators** showing whether variables came from config files or
  environment overrides

**Example Output:**

```
Template Variables:
 Variable         Value         Raw Value      Source       
 TB_MY_VAR        docker        ${DOCKER_CMD}  config       
 TB_OVERRIDE_VAR  env_override                 env          
 TB_STATIC        static_value                 config
```

This visibility helps users:

- Understand which variables are accessible to tools
- Identify variables that reference external environment variables
- Distinguish between config-defined and environment-overridden variables
- Debug configuration issues without exposing sensitive data

### Best Practices

1. **Use Approved Prefixes**: When setting environment variables for toolbelt,
   use the approved prefixes
2. **Avoid Sensitive Data**: Never use toolbelt to process files containing
   secrets
3. **Review Configuration**: Use `toolbelt config --show-variables` to verify
   which variables are accessible
4. **Environment Hygiene**: Be aware of what environment variables are set in
   your development and CI environments
5. **Audit Variable Sources**: Use `--show-variables` to verify that sensitive
   variables are not inadvertently accessible

### Migration from Unfiltered Access

If you were previously relying on unrestricted environment variable access:

1. Identify which variables your configuration needs
2. Either:
   - Rename variables to use approved prefixes, or
   - Reference them in config `variables` section for static capture during
     config loading
3. Test that all required variables are accessible via
   `toolbelt config --show-variables`
4. Use the visibility features to audit variable sources and ensure no sensitive
   data is exposed
