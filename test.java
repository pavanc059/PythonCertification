package com.aetna.mm.uiflow.controllers;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringReader;
import java.net.URLEncoder;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;

import net.sf.json.JSONObject;

import org.apache.commons.codec.binary.Base64;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.http.protocol.HTTP;
import org.ccil.cowan.tagsoup.Parser;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.xml.sax.InputSource;

import com.aetna.mm.cache.IATVAtvPrmLookupCache;
import com.aetna.mm.cache.IATVUserMsgCache;
import com.aetna.mm.core.util.DateUtil;
import com.aetna.mm.domain.ATVConstants;
import com.aetna.mm.domain.EditList;
import com.aetna.mm.domain.ErrorObject;
import com.aetna.mm.dto.lookups.ATVPRMLookupDTO;
import com.aetna.mm.dto.restapi.AppToken;
import com.aetna.mm.dto.restapi.UserToken;
import com.aetna.mm.uiflow.utils.RestAPIUtility;
import com.aetna.mm.xml.RestAPITagHandler;

/**
 * Controller class for REST API code changes. This class will retrieve token/refresh token and make final API Call 
 * 
 * <p>Controller class for REST API code changes. This class will retrieve token/refresh token and make final API Call</p>
 * 
 * <pre>
 * 
 *  Release		Author				Project/SR/Brief Description
 * --------	   --------		   		------------------------------
 *  Dec'16		Anurag Sharma		P08-8227j EBN 2a Controller class for REST API code changes. 
 *  								This class will retrieve token/refresh token and make final API Call
 * 
 * </pre>
 * 
 * @author N242616 Anurag Sharma
 * @since Dec 2016
 * 
 */

public class RestAPIRedirectController 
{	
    private Log logger = LogFactory.getLog(getClass());    
	//private static UserToken userToken;
	private String tokenUrl;
	private IATVAtvPrmLookupCache atvParmLkupCache;
	private String SAMLTOSSOUrl;
	private String redirect_uri;
	private String scope;
	private String apiEndPointPath;
	private String samlAuthorizeUrl;
	private String strClientId = "";
	private String strSecretKey = "";
	private static AppToken appToken;
	
	private IATVUserMsgCache userMSGLookup;
	/**
		 * @return the userMSGLookup
		 */
		public IATVUserMsgCache getUserMSGLookup() {
			return userMSGLookup;
		}

		/**
		 * @param userMSGLookup the userMSGLookup to set
		 */
		public void setUserMSGLookup(IATVUserMsgCache userMSGLookup) {
			this.userMSGLookup = userMSGLookup;
		}
	/**
	 * 
	 * @param request
	 * @param apiEndPoint
	 * @param isLoggingEnabled
	 * @param editList
	 * @return
	 */
   	public ResponseEntity<String> callDestinationAPI(HttpServletRequest request, String requestMethod,String apiTokenCallType, String apiEndPoint, Map<String, String> parametersMap, boolean isLoggingEnabled, EditList editList )
   	{
   		if (strSecretKey == null || strSecretKey.equalsIgnoreCase("") )// app secret may be present in multiple rows
   		{
			List<ATVPRMLookupDTO> appSecretParmList = atvParmLkupCache.getATVPRMs(ATVConstants.ATVPRM_JOB_TXT_J2EE, ATVConstants.ATVPRM_PGM_TXT_API_APP_SECRET, ATVConstants.ATVPRM_VERSION_1, DateUtil.today());
			if(null == appSecretParmList) {
				logger.error("App Secret key could not be located.");
			} else {
				for(ATVPRMLookupDTO parm : appSecretParmList) {
					// if row is active append the string to form the secret key
					if(ATVConstants.INDICATOR_YES.equalsIgnoreCase(parm.getStrParmInd()))
						strSecretKey += parm.getStrDescription().trim();
				}
			}
   		}

   		if (strClientId == null || strClientId.equalsIgnoreCase("") )// client id
   		{
			ATVPRMLookupDTO clientKeyParm = atvParmLkupCache.getATVPRM(ATVConstants.ATVPRM_JOB_TXT_J2EE, ATVConstants.ATVPRM_TYPE_TXT_API_CLIENT_KEY, ATVConstants.ATVPRM_VERSION_1, DateUtil.today());
			if(null != clientKeyParm) {
				strClientId = clientKeyParm.getStrDescription().trim();
			} else {
				logger.error("Client ID missing in ATVPRM for API call.");
			}
   		}		
   		//strClientId = "703116b1-f406-4682-8535-7af6416990d7";
   		// = "E2yW2kV8lL4hU1mG8qV5rK3rI5vY3rK7nC2xX7mW3iV6yB6vY7";
   		
		ResponseEntity<String> responseEntity=null;
		try{
			if(apiTokenCallType == null || apiTokenCallType.equalsIgnoreCase(""))
				apiTokenCallType = ATVConstants.USER_LEVEL; // defaulting it to USER_LEVEL
			
			if(apiTokenCallType.equalsIgnoreCase(ATVConstants.USER_LEVEL))
				getUserToken(request,isLoggingEnabled, editList);
			else
				appToken = getApplicationLevelToken(request,isLoggingEnabled, editList);
			
		}catch (Exception e) {
			if(apiTokenCallType.equalsIgnoreCase(ATVConstants.USER_LEVEL))
				request.getSession().setAttribute(ATVConstants.USER_TOKEN, null);
			else
				appToken = null;
			ErrorObject err = new ErrorObject();
			err.setEditCode(ATVConstants.API_GEN_EDIT_CD);
			err.setEditActionCode(ATVConstants.ACTION_INFO_EDIT);
			err.setEditDescription(userMSGLookup.getMessage(ATVConstants.COMMON_BUS_USER_MESS_TYPE, err.getEditCode(), DateUtil.today()));	
			editList.add(err);
			//e.printStackTrace();
		}
		if(requestMethod==null)
			 requestMethod= request.getMethod();
		HttpMethod httpmethod=null;
		if("POST".equalsIgnoreCase(requestMethod)){
			httpmethod=HttpMethod.POST;
		}else if("GET".equalsIgnoreCase(requestMethod)){
			httpmethod=HttpMethod.GET;
		}else if ("OPTIONS".equalsIgnoreCase(requestMethod)){
			httpmethod=HttpMethod.OPTIONS;
		}else if("PUT".equalsIgnoreCase(requestMethod)){
			httpmethod=HttpMethod.PUT;
		}else if("DELETE".equalsIgnoreCase(requestMethod)){
			httpmethod=HttpMethod.DELETE;
		}

		// Need to be removed... this is just for local working QA
		//strClientId = "703116b1-f406-4682-8535-7af6416990d7"; 
		
		HttpHeaders httpHeaders = buildCommonInputForAPICall(request,apiTokenCallType);
		
		// log url, headers and parameters
		if (isLoggingEnabled)
		{
			logger.error(httpmethod + " - url = " + apiEndPoint 
					+ ", headers = " + (httpHeaders != null ? httpHeaders.toString() : "") 
					+ ", params = " + (parametersMap != null ? parametersMap.toString() : ""));

			logger.error("Destination Rest API Call Start Time : " + DateUtil.today());
		}			
		if(httpmethod.equals(HttpMethod.OPTIONS))
		{
			//responseEntity = RestAPIUtility.restCallOptions(apiEndPoint, String.class,response,request);		
		}else
		{
			if(request.getHeader("Content-Type")!=null && request.getHeader("Content-Type").equalsIgnoreCase("application/json")){
				String jsonRequest=getJsonString(request);			
				responseEntity=	RestAPIUtility.restCallJSON(apiEndPoint, httpmethod, jsonRequest, httpHeaders, String.class);			
			}else{
				responseEntity = RestAPIUtility.restCall(apiEndPoint,httpmethod, null, null, httpHeaders, parametersMap, String.class);
			}
		}	
		
		if (isLoggingEnabled)
			logger.error("Destination Rest API Call End Time : " + DateUtil.today());
		
		if (isLoggingEnabled & responseEntity != null)
		{
			logger.error("Response Entity from final API call : " + responseEntity.getBody().toString());
		}
		
		return responseEntity;
	}   

   	/**
   	 * 
   	 * @param request
   	 * @return
   	 */
	private String getJsonString(HttpServletRequest request){
		BufferedReader reader=null;
		StringBuilder sb=null; 
	    try {
	        String line;
	         sb = new StringBuilder();
		     reader = request.getReader();
	        while ((line = reader.readLine()) != null) {
	            sb.append(line);
	        }
	    } catch(Exception e) {
	    	logger.error("error in reading request json");
	    } finally {
	        if(reader !=null){	        	
	        	try {
					reader.close();
				} catch (IOException e) {	
					
				}
	        }		        	
	    }
	    
	   return sb!=null?sb.toString():"{}";
	}
	
	/**
	 * This method helps getting the token used to make API call
	 * @param session
	 * @param editList
	 * @return API token
	 */
	private UserToken getUserToken(HttpServletRequest request, boolean isLoggingEnabled, EditList editList ) {

		UserToken userToken = (UserToken)request.getSession().getAttribute(ATVConstants.USER_TOKEN);
		if(null != userToken) {
			// Check if token is expired
			if(isUserTokenExpired(userToken)) 
			{
				if (userToken.getRefresh_token() != null){
					return refreshUserToken(request,isLoggingEnabled,editList);
				} else if(getFreshUserToken(request,isLoggingEnabled,editList)) {
					return (UserToken)request.getSession().getAttribute(ATVConstants.USER_TOKEN);
				} else
					return null;
			} else {
				// active token exists
				return userToken;
			}
		} else {
			// token does not exist
			if(getFreshUserToken(request,isLoggingEnabled,editList)) {
				return (UserToken)request.getSession().getAttribute(ATVConstants.USER_TOKEN);
			} else
				return null;
		}
	}
	
	/**
	 * 
	 * @param request
	 * @param isLoggingEnabled
	 * @param editList
	 * @return
	 */
	private boolean getFreshUserToken(HttpServletRequest request, boolean isLoggingEnabled, EditList editList )
	{			
	    RestAPITagHandler tagHandler = new RestAPITagHandler();
		boolean tokenFetched = false;

		if(null == editList)
			editList = new EditList();

		try 
		{												
			HttpHeaders httpHeaders = new HttpHeaders();
			String siteMinderCookie = "";
			Cookie siteMinderCookieServer = null;

			if("localhost".equalsIgnoreCase(request.getServerName())){
				siteMinderCookie = getSmSessionForLocal(request);
			}else{
				siteMinderCookieServer = getSmSessionForServer(request,isLoggingEnabled);
			}
			
			ResponseEntity<String> responseEntity=null;
			ResponseEntity<String> responseEntityCode=null;
			
			if (siteMinderCookieServer != null) // Uncomment this code when check in
			//if (siteMinderCookie != null) // Comment this code when check in
			{
				//for local
				if("localhost".equalsIgnoreCase(request.getServerName())){
					httpHeaders.add(ATVConstants.COOKIE,siteMinderCookie);
				}else{
					httpHeaders.add(ATVConstants.COOKIE, siteMinderCookieServer.getName() + "=" + siteMinderCookieServer.getValue());
				}
				try
				{
					if (isLoggingEnabled & siteMinderCookieServer != null)
					{
						logger.error("SM Session Cookie : " + siteMinderCookieServer.getName() + "=" + siteMinderCookieServer.getValue());
						logger.error("SAMLTOSSOUrl Final URL : " + getFinalSAMLToSSOURL());
						logger.error("SAMLTOSSOUrl Rest API Call Start Time : " + DateUtil.today());
					}
					responseEntity=	RestAPIUtility.restCallJSON(getFinalSAMLToSSOURL(),HttpMethod.GET, null, httpHeaders, String.class);	
					if (responseEntity != null & isLoggingEnabled)
					{
						logger.error("Response Entity Status from SSO Authorization Call : " + responseEntity.getBody());
						logger.error("Response Entity Status from SSO Authorization Call : " + responseEntity.getStatusCode());
						logger.error("Response Entity Headers from SSO Authorization Call : " + responseEntity.getHeaders());
						logger.error("SAMLTOSSOUrl Rest API Call End Time : " + DateUtil.today());
					}					
					StringReader inputStream = new StringReader(responseEntity.getBody());
				    InputSource source = new InputSource(inputStream);
				    Parser parser = new Parser();  
				    
				    parser.setContentHandler(tagHandler); 
				    parser.parse(source);
				    
					Map<String, String> parametersMapCode = new HashMap<String, String>();		
					parametersMapCode.put(ATVConstants.SAMLRESPONSE,tagHandler.getSamlPayload());
					String relayStateUrl = "response_type=code&client_id="+strClientId+"&redirect_uri="+redirect_uri+"&scope="+scope+"&path="+apiEndPointPath;

					//ATV DEV
					//relayStateUrl = "response_type=code&client_id=4a4500d5-d0f1-4384-86b0-00b9dec061ac&redirect_uri=https://dev3www20.aetna.com/atv5&scope=Public+NonPII+PII+PHI&path=devintpath1";

					//ATV QA
					//relayStateUrl ="response_type=code&client_id=703116b1-f406-4682-8535-7af6416990d7&redirect_uri=https://qa3www20.aetna.com/atv5&scope=Public+NonPII+PII+PHI&path=qaintpath1";
					//relayStateUrl ="response_type=code&client_id=703116b1-f406-4682-8535-7af6416990d7&redirect_uri=https://qa3www20.aetna.com/atv5&scope=Public NonPII PII PHI&path=qaintpath1";
					
					parametersMapCode.put(ATVConstants.RELAYSTATE,relayStateUrl);
					HttpHeaders httpHeadersCode = new HttpHeaders();

					if("localhost".equalsIgnoreCase(request.getServerName())){
						httpHeadersCode.add(ATVConstants.COOKIE,siteMinderCookie);
					}else{
						httpHeadersCode.add(ATVConstants.COOKIE, siteMinderCookieServer.getName() + "=" + siteMinderCookieServer.getValue());
					}
					httpHeadersCode.add(ATVConstants.CONTENT_TYPE,ATVConstants.URL_ENCODED_CONTENT);
					httpHeadersCode.add(ATVConstants.REFERER,getFinalSAMLToSSOURL());
					
					if (isLoggingEnabled)
					{
						logger.error("SAML Authorization URL : " + samlAuthorizeUrl);
						logger.error("RelayStateUrl : " + relayStateUrl);
						logger.error("SAML Authorization URL Rest API Call Start Time : " + DateUtil.today());
					}
					// DEV
					//responseEntityCode = RestAPIUtility.restCall("https://devapi2.aetna.com/healthcare/devintpath1/v3/auth/oauth2/samlauthorize",HttpMethod.POST, null, null, httpHeadersCode, parametersMapCode, String.class);
			
					// QA
					//responseEntityCode = RestAPIUtility.restCall("https://qaapi2.aetna.com/healthcare/qaintpath1/v3/auth/oauth2/samlauthorize",HttpMethod.POST, null, null, httpHeadersCode, parametersMapCode, String.class);
					
					responseEntityCode = RestAPIUtility.restCall(samlAuthorizeUrl,HttpMethod.POST, null, null, httpHeadersCode, parametersMapCode, String.class);
					
					if (responseEntityCode != null & isLoggingEnabled)
					{
						logger.error("Response Entity Code Object from SAML Authorization Call : " + responseEntityCode);
						logger.error("Response Entity Status from SAML Authorization Call : " + responseEntityCode.getStatusCode().value());
						logger.error("SAML Authorization URL Rest API Call End Time : " + DateUtil.today());
					}					
				}
				catch (Exception e)
				{
					logger.error("Error while SAML Assertion to get Auth Code"+e, e);
					ErrorObject err = new ErrorObject();
					err.setEditCode(ATVConstants.API_GEN_EDIT_CD);
					err.setEditActionCode(ATVConstants.ACTION_INFO_EDIT);
					err.setEditDescription(userMSGLookup.getMessage(ATVConstants.COMMON_BUS_USER_MESS_TYPE, err.getEditCode(), DateUtil.today()));	
					editList.add(err);
				}
				//The call to APIc if successful we get HttpStatusCode = 302. 
				//The location attribute in header has the redirect_uri with code.
				if (responseEntityCode != null )
				{
					if(responseEntityCode.getStatusCode().value() == 302)
					{											
						String strLocation = responseEntityCode.getHeaders().get(ATVConstants.LOCATION).get(0);					
						if (strLocation.contains(ATVConstants.CODE))
						{
							if (isLoggingEnabled)
								logger.error("strLocation from Rest API Call :" + strLocation );
							
							try
							{
								String[] str = strLocation.split("\\?");
								String grantType = ATVConstants.GRANT_TYPE_AUTHORIZATION_CODE;			
								HttpHeaders httpHeadersCode = new HttpHeaders();						
								
								MultiValueMap<String, String> map = new LinkedMultiValueMap<String, String>();
								
								map.add(ATVConstants.GRANT_TYPE, grantType);				
								map.add(ATVConstants.REDIRECT_URI, str[0]);			
								map.add(ATVConstants.CODE,str[1].substring(5));
								
								//Need to comment below lines before check in
								//strClientId = "703116b1-f406-4682-8535-7af6416990d7";
								//strSecretKey = "E2yW2kV8lL4hU1mG8qV5rK3rI5vY3rK7nC2xX7mW3iV6yB6vY7";
								
								String authorization = ATVConstants.BASIC + new String(Base64.encodeBase64((strClientId + ":" + strSecretKey).getBytes()));
								
								httpHeadersCode.add(ATVConstants.AUTHORIZATION, authorization);
								httpHeadersCode.add(ATVConstants.CONTENT_TYPE,ATVConstants.URL_ENCODED_CONTENT);
								
								HttpEntity<MultiValueMap<String, String>> entity = new HttpEntity<MultiValueMap<String, String>>(map, httpHeadersCode);
								
								if (isLoggingEnabled)
								{
									logger.error("User Level Token Rest API Call URL : " + tokenUrl);
									logger.error("User Level Token Rest API Call Start Time : " + DateUtil.today());
								}
								
								// DEV 
								//ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity("https://devapi2.aetna.com/healthcare/devintpath1/v3/auth/oauth2/token", entity, String.class);
					
						    	// QA
								//ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity("https://qaapi2.aetna.com/healthcare/qaintpath1/v3/auth/oauth2/token", entity, String.class);
								
								ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity(tokenUrl, entity, String.class);				    	
	
						    	// create new token
						    	// get json object from the response, check for error and populate token accordingly
								if (postResponseCode != null)
								{
									JSONObject jsonObject = JSONObject.fromObject(postResponseCode.getBody());
									
									UserToken userToken = new UserToken();
									long expiresIn = jsonObject.getLong(ATVConstants.EXPIRES_IN);
									userToken.setExpires_in(expiresIn);
									userToken.setAccess_token(jsonObject.getString(ATVConstants.ACCESS_TOKEN));
									userToken.setToken_type(jsonObject.getString(ATVConstants.TOKEN_TYPE));
									userToken.setScope(jsonObject.getString(ATVConstants.SCOPE));
									userToken.setRefresh_token(jsonObject.getString(ATVConstants.GRANT_TYPE_REFRESH_TOKEN));
									userToken.setAuthorization_code(str[1].substring(5));
									
									request.getSession().setAttribute(ATVConstants.USER_TOKEN, userToken);
									
									tokenFetched = true;
									
									if (isLoggingEnabled)
									{
										logger.error("User Level Token : "+ userToken.getAccess_token());
										logger.error("User Level Token Expiry Time : "+ new Date(userToken.getExpires_in()));
										logger.error("User Level Token Scope : "+ userToken.getScope());
										logger.error("User Level Token Type : "+ userToken.getToken_type());
										logger.error("User Level Token Rest API Call End Time : " + DateUtil.today());
										logger.error("User Level Token Refresh Token: "+ userToken.getRefresh_token());
									}
								} else {
									if (isLoggingEnabled)
										logger.error("User Level Token call failed: ");
								}
							}
							catch(Exception e){
								request.getSession().setAttribute(ATVConstants.USER_TOKEN, null);
								logger.error("Error while Calling Auth Code"+e, e);	
								ErrorObject err = new ErrorObject();
								err.setEditCode(ATVConstants.API_GEN_EDIT_CD);
								err.setEditActionCode(ATVConstants.ACTION_INFO_EDIT);
								err.setEditDescription(userMSGLookup.getMessage(ATVConstants.COMMON_BUS_USER_MESS_TYPE, err.getEditCode(), DateUtil.today()));	
								editList.add(err);
							}
						}
					}else if(responseEntityCode.getStatusCode().value() == 401)
					{
						request.getSession().setAttribute(ATVConstants.USER_TOKEN, null);
						if (isLoggingEnabled)
						{
							logger.error("Response Entity Code Object from SAML Authorization Call when Status Code: 401 : " + responseEntityCode);
							logger.error("Response Entity Status from SAML Authorization Call when Status Code: 401 : " + responseEntityCode.getStatusCode().value());
						}
					}else{
						request.getSession().setAttribute(ATVConstants.USER_TOKEN, null);
						if (isLoggingEnabled)
						{
							logger.error("Response Entity Code Object from SAML Authorization Call : " + responseEntityCode);
							logger.error("Response Entity Status from SAML Authorization Call : " + responseEntityCode.getStatusCode().value());
						}
					}   
				}
			}
			else if("localhost".equalsIgnoreCase(request.getServerName()))
			{   
				// Please copy below values from ATV Health Dashboard as we can't retrieve user token on local.
				long longMiliSecondsFromHealthDashboard = 0;
				String strAccesTokenFromHealthDashboard = "";
				//String strTokenScopeFromHealthDashboard = "";
				UserToken userToken = new UserToken();
				userToken.setExpires_in(longMiliSecondsFromHealthDashboard);
				userToken.setAccess_token(strAccesTokenFromHealthDashboard);
				userToken.setToken_type("bearer");
				userToken.setScope("Public NonPII PII PHI");
				request.getSession().setAttribute(ATVConstants.USER_TOKEN, userToken);
				tokenFetched = true;
			}
			else{
				tokenFetched= false;
			}
		}
		catch(Exception exception)
		{
			logger.error("Error while retrieving User level API Token" + exception.toString());
			
			ErrorObject err = new ErrorObject();
			err.setEditCode(ATVConstants.API_GEN_EDIT_CD);
			err.setEditActionCode(ATVConstants.ACTION_INFO_EDIT);
			err.setEditDescription(userMSGLookup.getMessage(ATVConstants.COMMON_BUS_USER_MESS_TYPE, err.getEditCode(), DateUtil.today()));	
			editList.add(err);
            throw exception;
		}
		return tokenFetched;
	}
	
	/**
	 * 
	 * @param request
	 * @return
	 */
	private String getSmSessionForLocal(HttpServletRequest request)
	{
		return null;
	}
	
	/**
	 * 
	 * @param request
	 * @param isLoggingEnabled
	 * @return
	 */
	private Cookie getSmSessionForServer(HttpServletRequest request, boolean isLoggingEnabled){
		
		Cookie siteMinderCookie = null;
		if (request.getCookies() != null)
			for (Cookie cookie : request.getCookies())
				if (cookie.getName().equalsIgnoreCase("SMSESSION"))
				{
					siteMinderCookie = cookie;
					if (isLoggingEnabled)
						logger.error("SMSESSION : " + cookie.getValue() );
				}
		
		if(siteMinderCookie==null){
			if (isLoggingEnabled)
				logger.error("No Siteminder Cookie");
		}
		
		return siteMinderCookie;
	}
	
	/**
	 * This method contains common code which sets the header parameters for calling any API.
	 * @param clientId
	 * @param request
	 * @return
	 */
	public HttpHeaders buildCommonInputForAPICall(HttpServletRequest request, String apiTokenCallType)
	{
		
		UserToken userToken = null;
		String authorizationValue = "";
		Map<String, String> headersMap = new HashMap<String, String>();			 
		
		if(apiTokenCallType != null && apiTokenCallType.equalsIgnoreCase(ATVConstants.USER_LEVEL))
		{	
			userToken = (UserToken)request.getSession().getAttribute(ATVConstants.USER_TOKEN);
			if (userToken != null)
				authorizationValue = "Bearer " + userToken.getAccess_token();
		
		} else {
			if (appToken != null && !appToken.getAccess_token().equalsIgnoreCase(""))
				authorizationValue = "Bearer " + appToken.getAccess_token();
		}
		
		headersMap.put("Accept", "application/xml");
	//	headersMap.put("Accept-Encoding", "gzip,deflate"); // Need to comment this line for handling unzipped data.
		headersMap.put("Connection", "Keep-Alive");
		headersMap.put("Authorization", authorizationValue);
		headersMap.put("X-IBM-Client-ID", strClientId);

		HttpHeaders httpHeaders = new HttpHeaders();
		for (String key : headersMap.keySet())
			httpHeaders.add(key, headersMap.get(key));
		
		httpHeaders.setContentType(MediaType.APPLICATION_XML); // setting content as XML for now.
		
		return httpHeaders;
	}
	
	/**
	 * 
	 * @param request
	 * @return
	 */
	public UserToken refreshUserToken(HttpServletRequest request,boolean isLoggingEnabled, EditList editList )
	{
		if(isLoggingEnabled)
			logger.error("In Refresh Token API Call Start:");
		
		UserToken userToken = (UserToken)request.getSession().getAttribute(ATVConstants.USER_TOKEN);
		HttpHeaders httpHeadersCode = new HttpHeaders();						
		MultiValueMap<String, String> map = new LinkedMultiValueMap<String, String>();
		
		map.add(ATVConstants.GRANT_TYPE, ATVConstants.GRANT_TYPE_REFRESH_TOKEN);
		map.add(ATVConstants.SCOPE, scope);
		map.add(ATVConstants.GRANT_TYPE_REFRESH_TOKEN,userToken.getRefresh_token());

		//Need to comment below lines before check in
		//strClientId = "703116b1-f406-4682-8535-7af6416990d7";
		//strSecretKey = "E2yW2kV8lL4hU1mG8qV5rK3rI5vY3rK7nC2xX7mW3iV6yB6vY7";
		
		String authorization = ATVConstants.BASIC + new String(Base64.encodeBase64((strClientId + ":" + strSecretKey).getBytes()));
		
		httpHeadersCode.add(ATVConstants.AUTHORIZATION, authorization);
		httpHeadersCode.add(ATVConstants.CONTENT_TYPE,ATVConstants.URL_ENCODED_CONTENT);
		
		HttpEntity<MultiValueMap<String, String>> entity = new HttpEntity<MultiValueMap<String, String>>(map, httpHeadersCode);
		
		// DEV 
		//ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity("https://devapi2.aetna.com/healthcare/devintpath1/v3/auth/oauth2/token", entity, String.class);

    	// QA
		//ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity("https://qaapi2.aetna.com/healthcare/qaintpath1/v3/auth/oauth2/token", entity, String.class);
		
		ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity(tokenUrl, entity, String.class);				    	

		if(isLoggingEnabled)
			logger.error("PostResponseCode from Refresh Token API Call " + postResponseCode);

    	// create new token
    	// get json object from the response, check for error and populate token accordingly
		if (postResponseCode != null)
		{
			JSONObject jsonObject = JSONObject.fromObject(postResponseCode.getBody());
			long expiresIn = jsonObject.getLong(ATVConstants.EXPIRES_IN);
			userToken.setExpires_in(expiresIn);
			userToken.setAccess_token(jsonObject.getString(ATVConstants.ACCESS_TOKEN));
			userToken.setToken_type(jsonObject.getString(ATVConstants.TOKEN_TYPE));
			userToken.setScope(jsonObject.getString(ATVConstants.SCOPE));
			userToken.setRefresh_token(jsonObject.getString(ATVConstants.GRANT_TYPE_REFRESH_TOKEN));
			
			request.getSession().setAttribute(ATVConstants.USER_TOKEN, userToken); // setting new token

			if(isLoggingEnabled)
				logger.error("User Token from Refresh Token Call " + userToken);

		}

		if(isLoggingEnabled)
			logger.error("In Refresh Token API Call End:");

		return userToken;
	}

	
	public AppToken getApplicationLevelToken(HttpServletRequest request, boolean isLoggingEnabled, EditList editList ) 
	{
		// ensure all the threads should have only one copy of token
		synchronized(this) {
			// check if token exist already
			if(null != appToken) {
				// Check if token is expired
				if(isAppTokenExpired(appToken)) {
					// remove old token and fetch new token
					appToken = null;
					if(getFreshAppToken(request, isLoggingEnabled, editList)) {
						return appToken;
					} else
						return null;
				} else {
					// active token exists
					return appToken;
				}
			} else {
				// token does not exist
				if(getFreshAppToken(request, isLoggingEnabled, editList)) {
					return appToken;
				} else
					return null;
			}
		}
	}

	/**
	 * Fetches fresh token for API call, when required
	 * @param session
	 * @param editList
	 * @return true if token is fetched successfully
	 */
	private boolean getFreshAppToken(HttpServletRequest request, boolean isLoggingEnabled, EditList editList )
	{
		if (isLoggingEnabled)
			logger.error("App Level Token Rest API Call Start Time : " + DateUtil.today());
		
		boolean tokenFetched = false;
		String authorization = ATVConstants.BASIC + new String(Base64.encodeBase64((strClientId + ":" + strSecretKey).getBytes()));

		// build post parameters
		MultiValueMap<String, String> map = new LinkedMultiValueMap<String, String>();
		map.add(ATVConstants.GRANT_TYPE, "client_credentials");
		map.add(ATVConstants.SCOPE, scope);
		
		HttpHeaders httpHeadersCode = new HttpHeaders();	
		httpHeadersCode.add(ATVConstants.AUTHORIZATION, authorization);
		httpHeadersCode.add(ATVConstants.CONTENT_TYPE,ATVConstants.URL_ENCODED_CONTENT);
		
		HttpEntity<MultiValueMap<String, String>> entity = new HttpEntity<MultiValueMap<String, String>>(map, httpHeadersCode);

    	// QA
		//ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity("https://qaapi2.aetna.com/healthcare/qaintpath1/v3/auth/oauth2/token", entity, String.class);
		
		ResponseEntity<String> postResponseCode = new RestTemplate().postForEntity(tokenUrl, entity, String.class);				    	

		if (postResponseCode != null )
		{
			// get json object from the response, check for error and populate token accordingly
			JSONObject jsonObj = JSONObject.fromObject(postResponseCode.getBody());
	
			// create new token
			appToken = new AppToken();
			long expiresIn = jsonObj.getLong("expires_in");
			appToken.setExpires_in(expiresIn);
			appToken.setAccess_token(jsonObj.getString("access_token"));
			appToken.setToken_type(jsonObj.getString("token_type"));
			appToken.setScope(jsonObj.getString("scope"));
	
			tokenFetched = true;
			
			if (isLoggingEnabled)
			{
				logger.error("App Level Token : "+ appToken.getAccess_token());
				logger.error("App Level Token Expiry Time : "+ new Date(appToken.getExpires_in()));
				logger.error("App Level Token Scope : "+ appToken.getScope());
				logger.error("App Level Token Type : "+ appToken.getToken_type());
				logger.error("App Level Token Rest API Call End Time : " + DateUtil.today());
			}
		}
		return tokenFetched;
	}


	/**
	 * 
	 * @param userToken
	 * @return
	 */
	public boolean isUserTokenExpired(UserToken userToken){
		return userToken.getExpires_in()-(System.currentTimeMillis())>45000?false:true;
		//return true;
	}
	
	/**
	 * 
	 * @param userToken
	 * @return
	 */
	public boolean isAppTokenExpired(AppToken appToken){
		//return true;
		return appToken.getExpires_in()-(System.currentTimeMillis())>35000?false:true;
	}
	/**
	 * @return the tokenUrl
	 */
	public String getTokenUrl() {
		return tokenUrl;
	}

	/**
	 * @param tokenUrl the tokenUrl to set
	 */
	public void setTokenUrl(String tokenUrl) {
		this.tokenUrl = tokenUrl;
	}
	/**
	 * @return the atvParmLkupCache
	 */
	public IATVAtvPrmLookupCache getAtvParmLkupCache() {
		return atvParmLkupCache;
	}

	/**
	 * @param atvParmLkupCache the atvParmLkupCache to set
	 */
	public void setAtvParmLkupCache(IATVAtvPrmLookupCache atvParmLkupCache) {
		this.atvParmLkupCache = atvParmLkupCache;
	}
	
	public String getSAMLTOSSOUrl() {
		return SAMLTOSSOUrl;
	}

	public void setSAMLTOSSOUrl(String sAMLTOSSOUrl) {
		SAMLTOSSOUrl = sAMLTOSSOUrl;
	}

	public String getRedirect_uri() {
		return redirect_uri;
	}

	public void setRedirect_uri(String redirect_uri) {
		this.redirect_uri = redirect_uri;
	}

	public String getScope() {
		return scope;
	}

	public void setScope(String scope) {
		this.scope = scope;
	}

	public String getApiEndPointPath() {
		return apiEndPointPath;
	}

	public void setApiEndPointPath(String apiEndPointPath) {
		this.apiEndPointPath = apiEndPointPath;
	}

	public String getSamlAuthorizeUrl() {
		return samlAuthorizeUrl;
	}

	public void setSamlAuthorizeUrl(String samlAuthorizeUrl) {
		this.samlAuthorizeUrl = samlAuthorizeUrl;
	}

	/**
	 * 
	 * @return
	 */
	public String getFinalSAMLToSSOURL() 
	{
		String strFinalSAMLToSSOURL = "";
		// build authorization query string...
		StringBuffer authorizationParameters = new StringBuffer();
		authorizationParameters.append(ATVConstants.RESPONSE_TYPE);
		authorizationParameters.append("=");
		authorizationParameters.append(ATVConstants.CODE);
		authorizationParameters.append("&");
		authorizationParameters.append(ATVConstants.CLIENT_ID);
		authorizationParameters.append("=");
		authorizationParameters.append(strClientId);
		authorizationParameters.append("&");
		authorizationParameters.append(ATVConstants.REDIRECT_URI);
		authorizationParameters.append("=");
		authorizationParameters.append(redirect_uri);
		authorizationParameters.append("&");
		authorizationParameters.append(ATVConstants.SCOPE);
		authorizationParameters.append("=");
		authorizationParameters.append(scope);
		authorizationParameters.append("&");
		authorizationParameters.append(ATVConstants.PATH);
		authorizationParameters.append("=");
		authorizationParameters.append(apiEndPointPath);
		
		try {
			strFinalSAMLToSSOURL = SAMLTOSSOUrl + URLEncoder.encode(authorizationParameters.toString(), HTTP.UTF_8);
		} catch (Exception e) {
		}
		//ATV Dev
		//strFinalSAMLToSSOURL = "https://apq.aetna.com/affwebservices/public/saml2sso?SPID=qaapi2&RelayState=response_type%3Dcode%26client_id%3D4a4500d5-d0f1-4384-86b0-00b9dec061ac%26redirect_uri%3Dhttps%3A%2F%2Fdev3www20.aetna.com%2Fatv5%26scope%3DPublic%20NonPII%20PII%20PHI%26path%3Ddevintpath1";

		//ATV QA
		//strFinalSAMLToSSOURL = "https://apq.aetna.com/affwebservices/public/saml2sso?SPID=qaapi2&RelayState=response_type%3Dcode%26client_id%3D703116b1-f406-4682-8535-7af6416990d7%26redirect_uri%3Dhttps%3A%2F%2Fqa3www20.aetna.com%2Fatv5%26scope%3DPublic%20NonPII%20PII%20PHI%26path%3Dqaintpath1";
		//strFinalSAMLToSSOURL = "https://apq.aetna.com/affwebservices/public/saml2sso?SPID=qaapi2&RelayState=response_type%3Dcode%26client_id%3D703116b1-f406-4682-8535-7af6416990d7%26redirect_uri%3Dhttps%3A%2F%2Fqa3www20.aetna.com%2Fatv5%26scope%3DPublic+NonPII+PII+PHI%26path%3Dqaintpath1";
		return strFinalSAMLToSSOURL;
	}
	
}
